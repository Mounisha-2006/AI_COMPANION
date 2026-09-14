from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.space import Space
from app.models.project import Project
from app.models.material import Material
from app.models.activity_event import ActivityEvent, ActivityEventType
from app.models.quiz import Quiz, QuizAnswer
from app.models.assessment import Assessment, AssessmentResponse
from app.models.mastery import ConceptMastery
from app.models.conversation import Conversation, Message
from app.models.recommendation import Recommendation
from app.models.ai_usage import AIUsage
from app.services.project_service import ProjectService
from app.services.growth_service import GrowthService
from app.schemas.analytics import (
    ActivityTimelinePoint,
    ProjectActivityMetrics,
    ProjectPerformanceMetrics,
    ProjectGrowthMetrics,
    ProjectAIMetrics,
    ProjectAnalyticsResponse,
    GlobalQuizActivity,
    GlobalAssessmentSummary,
    ProjectSummaryMetric,
    GlobalAnalyticsResponse,
)
from app.schemas.activity_event import ActivityEventResponse

class AnalyticsService:
    @classmethod
    def get_project_analytics(cls, db: Session, project_id: int, user_id: int) -> ProjectAnalyticsResponse:
        """
        Compute authenticated, strictly-scoped project analytics from actual stored application data.
        """
        project = ProjectService.get_project_by_id(db, project_id=project_id, user_id=user_id)

        # 1. Activity Metrics
        total_events = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.project_id == project_id, ActivityEvent.user_id == user_id)
            .count()
        )

        # Learning sessions: distinct calendar dates user engaged with this project
        active_dates = (
            db.query(func.strftime("%Y-%m-%d", ActivityEvent.created_at))
            .filter(ActivityEvent.project_id == project_id, ActivityEvent.user_id == user_id)
            .distinct()
            .all()
        )
        learning_sessions = len(active_dates)

        # Tutor questions: take max of logged TUTOR_QUESTION events or recorded user messages in conversation
        logged_tutor_events = (
            db.query(ActivityEvent)
            .filter(
                ActivityEvent.project_id == project_id,
                ActivityEvent.user_id == user_id,
                ActivityEvent.event_type == ActivityEventType.TUTOR_QUESTION.value
            )
            .count()
        )
        conv_user_msgs = (
            db.query(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(
                Conversation.project_id == project_id,
                Conversation.user_id == user_id,
                Message.role == "user"
            )
            .count()
        )
        tutor_questions = max(logged_tutor_events, conv_user_msgs)

        # Quizzes
        quizzes = db.query(Quiz).filter(Quiz.project_id == project_id, Quiz.user_id == user_id).all()
        quiz_attempts = len(quizzes)

        # Questions answered (quiz answers + assessment responses)
        quiz_answers = (
            db.query(QuizAnswer)
            .join(Quiz, QuizAnswer.quiz_id == Quiz.id)
            .filter(Quiz.project_id == project_id, Quiz.user_id == user_id)
            .all()
        )
        assessment_responses = (
            db.query(AssessmentResponse)
            .join(Assessment, AssessmentResponse.assessment_id == Assessment.id)
            .filter(Assessment.project_id == project_id, Assessment.user_id == user_id)
            .all()
        )
        questions_answered = len(quiz_answers) + len(assessment_responses)

        # Material interactions (uploaded, processed, deleted, replaced)
        material_interactions = (
            db.query(ActivityEvent)
            .filter(
                ActivityEvent.project_id == project_id,
                ActivityEvent.user_id == user_id,
                ActivityEvent.event_type.like("MATERIAL_%")
            )
            .count()
        )

        activity_metrics = ProjectActivityMetrics(
            learning_sessions=learning_sessions,
            total_events=total_events,
            tutor_questions=tutor_questions,
            quiz_attempts=quiz_attempts,
            questions_answered=questions_answered,
            material_interactions=material_interactions
        )

        # 2. Performance Metrics
        correct_quiz_answers = sum(1 for a in quiz_answers if a.is_correct)
        quiz_accuracy = (
            round((correct_quiz_answers / len(quiz_answers)) * 100, 1)
            if quiz_answers else 0.0
        )

        masteries = (
            db.query(ConceptMastery)
            .filter(ConceptMastery.project_id == project_id, ConceptMastery.user_id == user_id)
            .all()
        )
        current_mastery = (
            round(sum(m.mastery_score for m in masteries) / len(masteries), 1)
            if masteries else 0.0
        )
        concepts_mastered = [m.concept for m in masteries if m.mastery_score >= 75.0]
        concepts_needing_attention = [
            m.concept for m in masteries
            if m.mastery_score < 65.0 or (m.recent_mistakes_count or 0) > 0
        ]

        performance_metrics = ProjectPerformanceMetrics(
            quiz_accuracy=quiz_accuracy,
            current_mastery=current_mastery,
            concepts_mastered_count=len(concepts_mastered),
            concepts_mastered=concepts_mastered,
            concepts_needing_attention_count=len(concepts_needing_attention),
            concepts_needing_attention=concepts_needing_attention
        )

        # 3. Growth Metrics
        concepts_improving: List[str] = []
        concepts_stable: List[str] = []
        concepts_growth_attention: List[str] = []

        for m in masteries:
            curr = round(m.mastery_score, 1)
            prev = round(m.previous_score if m.previous_score is not None else curr, 1)
            if m.evidence_count == 1 and m.previous_score == 0.0 and curr > 0.0:
                prev = curr
            st = GrowthService.classify_status(prev, curr, m.recent_mistakes_count)
            if st == "Improving":
                concepts_improving.append(m.concept)
            elif st == "Stable":
                concepts_stable.append(m.concept)
            else:
                concepts_growth_attention.append(m.concept)

        completed_assessments = (
            db.query(Assessment)
            .filter(
                Assessment.project_id == project_id,
                Assessment.user_id == user_id,
                Assessment.status == "completed"
            )
            .order_by(Assessment.created_at.asc())
            .all()
        )
        completed_assessments_count = len(completed_assessments)
        avg_assessment_score = (
            round(
                sum(a.overall_score for a in completed_assessments if a.overall_score is not None)
                / completed_assessments_count,
                1
            )
            if completed_assessments_count > 0 else None
        )
        assessment_scores_trend = [
            {
                "id": a.id,
                "title": f"Assessment {a.id}",
                "score": a.overall_score,
                "date": a.created_at.strftime("%Y-%m-%d") if a.created_at else ""
            }
            for a in completed_assessments
        ]

        # Activity over time (last 14 days)
        timeline = cls._get_activity_timeline(
            db=db, user_id=user_id, project_id=project_id, days=14
        )

        growth_metrics = ProjectGrowthMetrics(
            concepts_improving_count=len(concepts_improving),
            concepts_improving=concepts_improving,
            concepts_stable_count=len(concepts_stable),
            concepts_stable=concepts_stable,
            concepts_needing_attention_count=len(concepts_growth_attention),
            concepts_needing_attention=concepts_growth_attention,
            average_assessment_score=avg_assessment_score,
            completed_assessments_count=completed_assessments_count,
            assessment_scores_trend=assessment_scores_trend,
            activity_over_time=timeline
        )

        # 4. AI Activity Metrics
        ai_generated_assessments = (
            db.query(Assessment)
            .filter(Assessment.project_id == project_id, Assessment.user_id == user_id)
            .count()
        )
        ai_evaluations = (
            db.query(AssessmentResponse)
            .join(Assessment, AssessmentResponse.assessment_id == Assessment.id)
            .filter(
                Assessment.project_id == project_id,
                Assessment.user_id == user_id,
                AssessmentResponse.score.isnot(None)
            )
            .count()
        )
        recommendations_generated = (
            db.query(Recommendation)
            .filter(Recommendation.project_id == project_id, Recommendation.user_id == user_id)
            .count()
        )

        ai_metrics = ProjectAIMetrics(
            tutor_interactions=tutor_questions,
            ai_generated_assessments=ai_generated_assessments,
            ai_evaluations=ai_evaluations,
            recommendations_generated=recommendations_generated
        )

        # Recent activities for this project
        recent_events = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.project_id == project_id, ActivityEvent.user_id == user_id)
            .order_by(ActivityEvent.created_at.desc())
            .limit(10)
            .all()
        )

        return ProjectAnalyticsResponse(
            project_id=project.id,
            project_name=project.name,
            activity=activity_metrics,
            performance=performance_metrics,
            growth=growth_metrics,
            ai_activity=ai_metrics,
            recent_activities=[ActivityEventResponse.model_validate(e) for e in recent_events]
        )

    @classmethod
    def get_global_analytics(cls, db: Session, user_id: int) -> GlobalAnalyticsResponse:
        """
        Compute aggregated user analytics across all spaces, projects, and activities for the authenticated user.
        """
        # Spaces & Projects
        total_spaces = db.query(Space).filter(Space.user_id == user_id).count()
        projects = (
            db.query(Project)
            .join(Space, Project.space_id == Space.id)
            .filter(Space.user_id == user_id)
            .all()
        )
        total_projects = len(projects)

        # Total learning activity & active days
        total_learning_activity = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.user_id == user_id)
            .count()
        )
        active_dates = (
            db.query(func.strftime("%Y-%m-%d", ActivityEvent.created_at))
            .filter(ActivityEvent.user_id == user_id)
            .distinct()
            .all()
        )
        active_days = len(active_dates)

        # Quizzes across all user projects
        quizzes = db.query(Quiz).filter(Quiz.user_id == user_id).all()
        quizzes_started = len(quizzes)
        quizzes_completed = sum(1 for q in quizzes if q.status == "completed")

        quiz_answers = (
            db.query(QuizAnswer)
            .join(Quiz, QuizAnswer.quiz_id == Quiz.id)
            .filter(Quiz.user_id == user_id)
            .all()
        )
        total_quiz_answers = len(quiz_answers)
        correct_quiz_answers = sum(1 for a in quiz_answers if a.is_correct)
        quiz_accuracy = (
            round((correct_quiz_answers / total_quiz_answers) * 100, 1)
            if total_quiz_answers > 0 else 0.0
        )

        quiz_activity = GlobalQuizActivity(
            quizzes_started=quizzes_started,
            quizzes_completed=quizzes_completed,
            questions_answered=total_quiz_answers,
            quiz_accuracy=quiz_accuracy
        )

        # Masteries across all user projects
        masteries = db.query(ConceptMastery).filter(ConceptMastery.user_id == user_id).all()
        overall_mastery = (
            round(sum(m.mastery_score for m in masteries) / len(masteries), 1)
            if masteries else 0.0
        )

        concepts_improving = 0
        concepts_requiring_attention = 0
        concepts_stable = 0

        for m in masteries:
            curr = round(m.mastery_score, 1)
            prev = round(m.previous_score if m.previous_score is not None else curr, 1)
            if m.evidence_count == 1 and m.previous_score == 0.0 and curr > 0.0:
                prev = curr
            st = GrowthService.classify_status(prev, curr, m.recent_mistakes_count)
            if st == "Improving":
                concepts_improving += 1
            elif st == "Stable":
                concepts_stable += 1
            else:
                concepts_requiring_attention += 1

        # Assessments across all user projects
        all_assessments = db.query(Assessment).filter(Assessment.user_id == user_id).all()
        assessments_started = len(all_assessments)
        completed_assessments = [a for a in all_assessments if a.status == "completed"]
        assessments_completed = len(completed_assessments)
        avg_assessment_perf = (
            round(
                sum(a.overall_score for a in completed_assessments if a.overall_score is not None)
                / assessments_completed,
                1
            )
            if assessments_completed > 0 else None
        )
        assessment_history = [
            {
                "id": a.id,
                "project_id": a.project_id,
                "score": a.overall_score,
                "date": a.created_at.strftime("%Y-%m-%d") if a.created_at else ""
            }
            for a in sorted(completed_assessments, key=lambda x: x.created_at or datetime.min, reverse=True)[:10]
        ]
        assessment_performance = GlobalAssessmentSummary(
            assessments_started=assessments_started,
            assessments_completed=assessments_completed,
            average_score=avg_assessment_perf,
            history=assessment_history
        )

        # Tutor questions & Total questions asked
        logged_tutor_events = (
            db.query(ActivityEvent)
            .filter(
                ActivityEvent.user_id == user_id,
                ActivityEvent.event_type == ActivityEventType.TUTOR_QUESTION.value
            )
            .count()
        )
        conv_user_msgs = (
            db.query(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(Conversation.user_id == user_id, Message.role == "user")
            .count()
        )
        tutor_interactions = max(logged_tutor_events, conv_user_msgs)

        assessment_responses_count = (
            db.query(AssessmentResponse)
            .join(Assessment, AssessmentResponse.assessment_id == Assessment.id)
            .filter(Assessment.user_id == user_id)
            .count()
        )
        questions_asked = tutor_interactions + total_quiz_answers + assessment_responses_count

        # AI-generated feedback: evaluations + recommendations
        ai_evaluations = (
            db.query(AssessmentResponse)
            .join(Assessment, AssessmentResponse.assessment_id == Assessment.id)
            .filter(Assessment.user_id == user_id, AssessmentResponse.score.isnot(None))
            .count()
        )
        total_recs = db.query(Recommendation).filter(Recommendation.user_id == user_id).count()
        ai_generated_feedback = ai_evaluations + total_recs

        # Timeline across all projects (last 14 days)
        learning_activity_over_time = cls._get_activity_timeline(
            db=db, user_id=user_id, project_id=None, days=14
        )

        # Projects breakdown
        projects_breakdown: List[ProjectSummaryMetric] = []
        mastery_over_time: List[Dict[str, Any]] = []

        for p in projects:
            p_masteries = [m for m in masteries if m.project_id == p.id]
            p_score = (
                round(sum(m.mastery_score for m in p_masteries) / len(p_masteries), 1)
                if p_masteries else 0.0
            )
            p_quizzes = sum(1 for q in quizzes if q.project_id == p.id)
            p_tutor = sum(
                1 for m in db.query(Message)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .filter(Conversation.project_id == p.id, Conversation.user_id == user_id, Message.role == "user")
                .all()
            )
            p_materials = db.query(Material).filter(Material.project_id == p.id).count()

            projects_breakdown.append(
                ProjectSummaryMetric(
                    project_id=p.id,
                    project_name=p.name,
                    space_name=p.space.name if p.space else "Space",
                    mastery_score=p_score,
                    quiz_count=p_quizzes,
                    tutor_questions=p_tutor,
                    materials_count=p_materials,
                    created_at=p.created_at
                )
            )

            mastery_over_time.append({
                "project_id": p.id,
                "project_name": p.name,
                "mastery_score": p_score
            })

        # Recent activities
        recent_events = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.user_id == user_id)
            .order_by(ActivityEvent.created_at.desc())
            .limit(15)
            .all()
        )

        return GlobalAnalyticsResponse(
            total_learning_activity=total_learning_activity,
            active_days=active_days,
            total_spaces=total_spaces,
            total_projects=total_projects,
            overall_mastery=overall_mastery,
            average_assessment_performance=avg_assessment_perf,
            concepts_improving=concepts_improving,
            concepts_requiring_attention=concepts_requiring_attention,
            tutor_interactions=tutor_interactions,
            questions_asked=questions_asked,
            quiz_activity=quiz_activity,
            ai_generated_feedback=ai_generated_feedback,
            learning_activity_over_time=learning_activity_over_time,
            mastery_over_time=mastery_over_time,
            assessment_performance=assessment_performance,
            projects_breakdown=projects_breakdown,
            recent_activities=[ActivityEventResponse.model_validate(e) for e in recent_events]
        )

    @classmethod
    def _get_activity_timeline(
        cls,
        db: Session,
        user_id: int,
        project_id: Optional[int] = None,
        days: int = 14
    ) -> List[ActivityTimelinePoint]:
        """
        Generate a daily activity timeline for the specified window up to today.
        """
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

        query = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.user_id == user_id, ActivityEvent.created_at >= start_date)
        )
        if project_id is not None:
            query = query.filter(ActivityEvent.project_id == project_id)

        events = query.all()

        # Group by YYYY-MM-DD
        counts_by_date: Dict[str, int] = defaultdict(int)
        types_by_date: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for ev in events:
            if ev.created_at:
                date_str = ev.created_at.strftime("%Y-%m-%d")
                counts_by_date[date_str] += 1
                types_by_date[date_str][ev.event_type] += 1

        timeline: List[ActivityTimelinePoint] = []
        for d in range(days):
            day_dt = start_date + timedelta(days=d)
            day_str = day_dt.strftime("%Y-%m-%d")
            timeline.append(
                ActivityTimelinePoint(
                    date=day_str,
                    count=counts_by_date[day_str],
                    event_types=dict(types_by_date[day_str])
                )
            )

        return timeline
