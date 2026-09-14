import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from fastapi import HTTPException, status

from app.models.user import User
from app.models.space import Space
from app.models.project import Project
from app.models.material import Material, MaterialStatus
from app.models.activity_event import ActivityEvent, ActivityEventType
from app.models.quiz import Quiz, QuizAnswer
from app.models.assessment import Assessment, AssessmentResponse
from app.models.mastery import ConceptMastery
from app.models.conversation import Conversation, Message
from app.models.ai_usage import AIUsage
from app.services.ai_service import AIService
from app.services.growth_service import GrowthService
from app.schemas.admin import (
    AdminOverviewKPIs,
    AdminUserSummary,
    AdminProjectSummary,
    AdminOverviewResponse,
    AdminUserDetailResponse,
    AdminUserSpaceItem,
    AdminUserProjectItem,
    AdminUserInspectResponse,
    AdminAIUsageItem,
    AdminAIUsageResponse,
    AIEvaluationBenchmarkItem,
    AdminAIEvaluationResponse,
    AdminSystemHealthResponse
)
from app.schemas.activity_event import ActivityEventResponse

class AdminService:
    @classmethod
    def get_overview(cls, db: Session) -> AdminOverviewResponse:
        """
        Aggregate platform-wide KPIs and recent activity for the Admin Overview.
        """
        total_users = db.query(User).count()
        total_spaces = db.query(Space).count()
        total_projects = db.query(Project).count()
        total_materials = db.query(Material).count()

        logged_tutor_events = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.event_type == ActivityEventType.TUTOR_QUESTION.value)
            .count()
        )
        total_messages = db.query(Message).filter(Message.role == "user").count()
        total_tutor_interactions = max(logged_tutor_events, total_messages)

        total_quizzes = db.query(Quiz).count()
        total_assessments = db.query(Assessment).count()

        kpis = AdminOverviewKPIs(
            total_users=total_users,
            total_spaces=total_spaces,
            total_projects=total_projects,
            total_materials=total_materials,
            total_tutor_interactions=total_tutor_interactions,
            total_quizzes=total_quizzes,
            total_assessments=total_assessments
        )

        # Recent users (latest 5)
        latest_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
        recent_users_summary: List[AdminUserSummary] = []
        for u in latest_users:
            s_count = len(u.spaces) if u.spaces else 0
            p_count = sum(len(s.projects) for s in u.spaces) if u.spaces else 0
            q_count = len(u.quizzes) if u.quizzes else 0
            m_scores = [m.mastery_score for m in u.concept_masteries] if u.concept_masteries else []
            overall_m = round(sum(m_scores) / len(m_scores), 1) if m_scores else 0.0
            recent_users_summary.append(
                AdminUserSummary(
                    id=u.id,
                    name=u.name,
                    email=u.email,
                    role=u.role,
                    created_at=u.created_at,
                    spaces_count=s_count,
                    projects_count=p_count,
                    quizzes_count=q_count,
                    overall_mastery=overall_m
                )
            )

        # Recent projects (latest 5)
        latest_projects = db.query(Project).order_by(Project.created_at.desc()).limit(5).all()
        recent_projects_summary: List[AdminProjectSummary] = []
        for p in latest_projects:
            recent_projects_summary.append(
                AdminProjectSummary(
                    id=p.id,
                    name=p.name,
                    space_name=p.space.name if p.space else "Space",
                    user_email=p.space.user.email if p.space and p.space.user else "Unknown",
                    materials_count=len(p.materials) if p.materials else 0,
                    created_at=p.created_at
                )
            )

        # Recent activity events (latest 10)
        recent_activities = (
            db.query(ActivityEvent)
            .order_by(ActivityEvent.created_at.desc())
            .limit(10)
            .all()
        )

        # Recent material processing events (latest 10)
        recent_mat_events = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.event_type.like("MATERIAL_%"))
            .order_by(ActivityEvent.created_at.desc())
            .limit(10)
            .all()
        )

        return AdminOverviewResponse(
            kpis=kpis,
            recent_users=recent_users_summary,
            recent_projects=recent_projects_summary,
            recent_activity_events=[ActivityEventResponse.model_validate(e) for e in recent_activities],
            recent_material_events=[ActivityEventResponse.model_validate(e) for e in recent_mat_events]
        )

    @classmethod
    def list_users(
        cls,
        db: Session,
        limit: int = 50,
        skip: int = 0,
        search: Optional[str] = None
    ) -> List[AdminUserDetailResponse]:
        """
        List all users with aggregated activity & progress metrics for admin inspection.
        """
        query = db.query(User)
        if search:
            s = f"%{search.strip()}%"
            query = query.filter((User.name.ilike(s)) | (User.email.ilike(s)))

        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

        results: List[AdminUserDetailResponse] = []
        for u in users:
            s_count = len(u.spaces) if u.spaces else 0
            p_count = sum(len(s.projects) for s in u.spaces) if u.spaces else 0
            q_count = len(u.quizzes) if u.quizzes else 0

            # Count tutor questions
            t_count = max(
                db.query(ActivityEvent).filter(ActivityEvent.user_id == u.id, ActivityEvent.event_type == ActivityEventType.TUTOR_QUESTION.value).count(),
                db.query(Message).join(Conversation).filter(Conversation.user_id == u.id, Message.role == "user").count()
            )

            m_scores = [m.mastery_score for m in u.concept_masteries] if u.concept_masteries else []
            overall_m = round(sum(m_scores) / len(m_scores), 1) if m_scores else 0.0

            results.append(
                AdminUserDetailResponse(
                    id=u.id,
                    name=u.name,
                    email=u.email,
                    role=u.role,
                    created_at=u.created_at,
                    spaces_count=s_count,
                    projects_count=p_count,
                    quizzes_count=q_count,
                    tutor_questions_count=t_count,
                    overall_mastery=overall_m
                )
            )

        return results

    @classmethod
    def inspect_user(cls, db: Session, user_id: int) -> AdminUserInspectResponse:
        """
        Retrieve comprehensive, observation-only details for a specific user.
        Does not allow modifying user data.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found."
            )

        # Spaces & Projects
        spaces_items: List[AdminUserSpaceItem] = []
        projects_items: List[AdminUserProjectItem] = []

        for s in (user.spaces or []):
            spaces_items.append(
                AdminUserSpaceItem(
                    id=s.id,
                    name=s.name,
                    description=s.description,
                    projects_count=len(s.projects) if s.projects else 0,
                    created_at=s.created_at
                )
            )
            for p in (s.projects or []):
                p_masteries = [m for m in (user.concept_masteries or []) if m.project_id == p.id]
                p_score = (
                    round(sum(m.mastery_score for m in p_masteries) / len(p_masteries), 1)
                    if p_masteries else 0.0
                )
                projects_items.append(
                    AdminUserProjectItem(
                        id=p.id,
                        name=p.name,
                        space_name=s.name,
                        learning_goal=p.learning_goal,
                        materials_count=len(p.materials) if p.materials else 0,
                        mastery_score=p_score,
                        created_at=p.created_at
                    )
                )

        # Recent activities (latest 20)
        activities = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.user_id == user_id)
            .order_by(ActivityEvent.created_at.desc())
            .limit(20)
            .all()
        )

        # Concept masteries
        masteries = (
            db.query(ConceptMastery)
            .filter(ConceptMastery.user_id == user_id)
            .order_by(ConceptMastery.mastery_score.desc())
            .all()
        )
        mastery_breakdown: List[Dict[str, Any]] = []
        for m in masteries:
            curr = round(m.mastery_score, 1)
            prev = round(m.previous_score if m.previous_score is not None else curr, 1)
            st = GrowthService.classify_status(prev, curr, m.recent_mistakes_count)
            mastery_breakdown.append({
                "concept": m.concept,
                "project_id": m.project_id,
                "mastery_score": curr,
                "confidence": round(m.confidence, 2),
                "evidence_count": m.evidence_count,
                "recent_mistakes": m.recent_mistakes_count,
                "status": st
            })

        # Completed assessments
        assessments = (
            db.query(Assessment)
            .filter(Assessment.user_id == user_id, Assessment.status == "completed")
            .order_by(Assessment.created_at.desc())
            .all()
        )
        completed_assessments: List[Dict[str, Any]] = []
        for a in assessments:
            completed_assessments.append({
                "id": a.id,
                "project_id": a.project_id,
                "overall_score": a.overall_score,
                "total_questions": a.total_questions,
                "completed_at": a.completed_at.strftime("%Y-%m-%d %H:%M") if a.completed_at else ""
            })

        # Quiz accuracy
        quiz_answers = (
            db.query(QuizAnswer)
            .join(Quiz, QuizAnswer.quiz_id == Quiz.id)
            .filter(Quiz.user_id == user_id)
            .all()
        )
        total_answers = len(quiz_answers)
        correct_answers = sum(1 for a in quiz_answers if a.is_correct)
        quiz_acc = round((correct_answers / total_answers) * 100, 1) if total_answers > 0 else 0.0
        total_quiz_attempts = db.query(Quiz).filter(Quiz.user_id == user_id).count()

        # User detail header
        t_count = max(
            db.query(ActivityEvent).filter(ActivityEvent.user_id == user.id, ActivityEvent.event_type == ActivityEventType.TUTOR_QUESTION.value).count(),
            db.query(Message).join(Conversation).filter(Conversation.user_id == user.id, Message.role == "user").count()
        )
        overall_m = (
            round(sum(m.mastery_score for m in masteries) / len(masteries), 1)
            if masteries else 0.0
        )
        user_detail = AdminUserDetailResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            spaces_count=len(spaces_items),
            projects_count=len(projects_items),
            quizzes_count=total_quiz_attempts,
            tutor_questions_count=t_count,
            overall_mastery=overall_m
        )

        return AdminUserInspectResponse(
            user=user_detail,
            spaces=spaces_items,
            projects=projects_items,
            activities=[ActivityEventResponse.model_validate(e) for e in activities],
            mastery_breakdown=mastery_breakdown,
            completed_assessments=completed_assessments,
            quiz_accuracy=quiz_acc,
            total_quiz_attempts=total_quiz_attempts
        )

    @classmethod
    def get_ai_usage(cls, db: Session, limit: int = 50) -> AdminAIUsageResponse:
        """
        Aggregate genuine AI usage data without inventing token/cost numbers.
        """
        total_requests = db.query(AIUsage).count()

        # Feature breakdown
        features = db.query(AIUsage.feature, func.count(AIUsage.id)).group_by(AIUsage.feature).all()
        feature_breakdown = {f[0]: f[1] for f in features}

        # Model breakdown
        models = db.query(AIUsage.model, func.count(AIUsage.id)).group_by(AIUsage.model).all()
        model_breakdown = {m[0] or "default": m[1] for m in models}

        # Latency stats
        avg_lat = db.query(func.avg(AIUsage.latency_ms)).filter(AIUsage.latency_ms.isnot(None)).scalar()
        min_lat = db.query(func.min(AIUsage.latency_ms)).filter(AIUsage.latency_ms.isnot(None)).scalar()
        max_lat = db.query(func.max(AIUsage.latency_ms)).filter(AIUsage.latency_ms.isnot(None)).scalar()

        latency_stats = {
            "avg_latency_ms": round(avg_lat, 1) if avg_lat is not None else 0.0,
            "min_latency_ms": min_lat if min_lat is not None else 0,
            "max_latency_ms": max_lat if max_lat is not None else 0
        }

        # Token usage: actual stored values, otherwise "Not available"
        prompt_tok = db.query(func.sum(AIUsage.prompt_tokens)).filter(AIUsage.prompt_tokens.isnot(None)).scalar()
        comp_tok = db.query(func.sum(AIUsage.completion_tokens)).filter(AIUsage.completion_tokens.isnot(None)).scalar()
        tot_tok = db.query(func.sum(AIUsage.total_tokens)).filter(AIUsage.total_tokens.isnot(None)).scalar()

        has_tokens = tot_tok is not None and tot_tok > 0
        token_usage = {
            "prompt_tokens": prompt_tok if has_tokens else None,
            "completion_tokens": comp_tok if has_tokens else None,
            "total_tokens": tot_tok if has_tokens else None,
            "display_text": f"{tot_tok:,} tokens" if has_tokens else "Not available"
        }

        # Estimated cost: explicitly "Not available" as instructed (never invent values)
        estimated_cost = {
            "currency": "USD",
            "amount": None,
            "display_text": "Not available"
        }

        # Error count & success rate
        error_count = db.query(AIUsage).filter(AIUsage.success == False).count()
        success_rate = (
            round(((total_requests - error_count) / total_requests) * 100, 1)
            if total_requests > 0 else 100.0
        )

        recent = (
            db.query(AIUsage)
            .order_by(AIUsage.created_at.desc())
            .limit(limit)
            .all()
        )

        return AdminAIUsageResponse(
            total_requests=total_requests,
            feature_breakdown=feature_breakdown,
            model_breakdown=model_breakdown,
            latency_stats=latency_stats,
            token_usage=token_usage,
            estimated_cost=estimated_cost,
            error_count=error_count,
            success_rate=success_rate,
            recent_requests=[AdminAIUsageItem.model_validate(r) for r in recent]
        )

    @classmethod
    def get_ai_evaluation(cls, db: Session) -> AdminAIEvaluationResponse:
        """
        Fetch metrics from actual stored evaluation/test results.
        """
        # Tutor evaluation stats from activity events
        tutor_events = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.event_type == ActivityEventType.TUTOR_QUESTION.value)
            .all()
        )
        grounded_count = sum(1 for e in tutor_events if (e.metadata_json or {}).get("grounded") is True)
        grounded_rate = round((grounded_count / len(tutor_events)) * 100, 1) if tutor_events else 100.0
        total_sources_cited = sum((e.metadata_json or {}).get("source_count", 0) for e in tutor_events)

        tutor_eval = {
            "total_questions": len(tutor_events),
            "grounded_questions_count": grounded_count,
            "grounded_rate": grounded_rate,
            "sources_cited_count": total_sources_cited
        }

        # Assessment evaluation stats
        eval_responses = (
            db.query(AssessmentResponse)
            .filter(AssessmentResponse.score.isnot(None))
            .all()
        )
        total_evals = len(eval_responses)
        avg_score = round(sum(r.score for r in eval_responses) / total_evals, 1) if total_evals else 0.0
        strengths_found = sum(len(r.strengths or []) for r in eval_responses)
        missing_found = sum(len(r.missing_concepts or []) for r in eval_responses)

        assessment_eval = {
            "total_evaluations": total_evals,
            "average_score": avg_score,
            "strengths_identified_count": strengths_found,
            "missing_concepts_identified_count": missing_found
        }

        # AI errors
        ai_errors = db.query(AIUsage).filter(AIUsage.success == False).count()

        # Default benchmark items
        benchmarks = cls._run_benchmarks(db)

        return AdminAIEvaluationResponse(
            tutor_evaluation=tutor_eval,
            assessment_evaluation=assessment_eval,
            ai_errors_count=ai_errors,
            benchmark_results=benchmarks
        )

    @classmethod
    def _run_benchmarks(cls, db: Session) -> List[AIEvaluationBenchmarkItem]:
        """
        Execute basic evaluation tests verifying grounded synthesis, code generation, and unsupported query handling.
        """
        test_cases = [
            {
                "name": "Hello World Code Generation",
                "category": "Code Generation & Syntax",
                "query": "Write a Python program for Hello World",
                "context": [{"chunk_id": 1, "material_id": 1, "chunk_text": "To print Hello World: print('Hello, World!')", "page_number": 6}],
                "validate": lambda r: 'print("Hello, World!")' in r["answer"] or "print('Hello, World!')" in r["answer"],
                "expect_grounded": True
            },
            {
                "name": "Unsupported Query Rejection",
                "category": "Safety & Rejection",
                "query": "What is the capital of France?",
                "context": [{"chunk_id": 1, "material_id": 1, "chunk_text": "Python variables and data types", "page_number": 1}],
                "validate": lambda r: r["grounded"] is False and ("not available" in r["answer"].lower() or "could not find" in r["answer"].lower()),
                "expect_grounded": False
            },
            {
                "name": "List Indexing Understanding",
                "category": "Concept Synthesizer",
                "query": "What is the first index of a Python list?",
                "context": [{"chunk_id": 1, "material_id": 1, "chunk_text": "Lists in Python are indexed starting at 0.", "page_number": 24}],
                "validate": lambda r: "0" in r["answer"] and "zero-based" in r["answer"].lower(),
                "expect_grounded": True
            },
            {
                "name": "Variables & Storage",
                "category": "Concept Synthesizer",
                "query": "Explain variables in Python",
                "context": [{"chunk_id": 1, "material_id": 1, "chunk_text": "Variables in Python are named references that store values.", "page_number": 8}],
                "validate": lambda r: "named container" in r["answer"].lower() or "store" in r["answer"].lower(),
                "expect_grounded": True
            }
        ]

        results: List[AIEvaluationBenchmarkItem] = []
        for tc in test_cases:
            t0 = time.time()
            try:
                ans_data = AIService.generate_grounded_answer(
                    db=db,
                    user_id=1,
                    project_id=1,
                    question=tc["query"],
                    context_chunks=tc["context"]
                )
                lat_ms = int((time.time() - t0) * 1000)
                passed = tc["validate"](ans_data)
                status_str = "PASS" if passed else "FAIL"
                details = f"Grounded={ans_data.get('grounded')}, Citations={len(ans_data.get('sources', []))}, Answer length={len(ans_data.get('answer', ''))}"
            except Exception as exc:
                lat_ms = int((time.time() - t0) * 1000)
                status_str = "FAIL"
                details = f"Exception: {str(exc)}"

            results.append(
                AIEvaluationBenchmarkItem(
                    test_name=tc["name"],
                    category=tc["category"],
                    input_query=tc["query"],
                    status=status_str,
                    latency_ms=lat_ms,
                    details=details
                )
            )

        return results

    @classmethod
    def get_system_health(cls, db: Session) -> AdminSystemHealthResponse:
        """
        Lightweight system health monitor with zero secret exposure.
        """
        # 1. Database Health
        t0 = time.time()
        db_connected = True
        try:
            db.execute(text("SELECT 1;")).fetchone()
            db_latency = round((time.time() - t0) * 1000, 2)
        except Exception:
            db_connected = False
            db_latency = 0.0

        database_info = {
            "status": "connected" if db_connected else "disconnected",
            "latency_ms": db_latency,
            "engine": "SQLite"
        }

        # 2. AI Provider Health
        ai_provider_info = {
            "status": "operational",
            "mode": "grounded-rag-synthesizer",
            "model": "local-grounded-synthesizer"
        }

        # 3. Background Processing Status
        queued = db.query(Material).filter(Material.status == MaterialStatus.QUEUED.value).count()
        processing = db.query(Material).filter(Material.status == MaterialStatus.PROCESSING.value).count()
        backlog = queued + processing
        bg_status = "idle" if backlog == 0 else "busy"

        background_queue = {
            "status": bg_status,
            "queued_count": queued,
            "processing_count": processing,
            "backlog": backlog
        }

        # 4. Latency & Error metrics
        avg_lat = db.query(func.avg(AIUsage.latency_ms)).filter(AIUsage.latency_ms.isnot(None)).scalar()
        average_ai_latency_ms = round(avg_lat, 1) if avg_lat is not None else 0.0

        total_ai = db.query(AIUsage).count()
        failed_ai = db.query(AIUsage).filter(AIUsage.success == False).count()
        ai_error_rate = round((failed_ai / total_ai) * 100, 2) if total_ai > 0 else 0.0

        # 5. Recent Failures
        failed_materials = (
            db.query(Material)
            .filter(Material.status == MaterialStatus.FAILED.value)
            .order_by(Material.updated_at.desc())
            .limit(5)
            .all()
        )
        failed_events = (
            db.query(ActivityEvent)
            .filter(ActivityEvent.event_type.like("%_FAILED"))
            .order_by(ActivityEvent.created_at.desc())
            .limit(5)
            .all()
        )

        recent_failures: List[Dict[str, Any]] = []
        for fm in failed_materials:
            recent_failures.append({
                "type": "Material Processing Failure",
                "target": fm.filename,
                "detail": fm.error_message or "Unknown processing error",
                "timestamp": fm.updated_at.strftime("%Y-%m-%d %H:%M") if fm.updated_at else ""
            })
        for fe in failed_events:
            recent_failures.append({
                "type": fe.event_type,
                "target": f"Project {fe.project_id or 'General'}",
                "detail": (fe.metadata_json or {}).get("error") or "Operation failed",
                "timestamp": fe.created_at.strftime("%Y-%m-%d %H:%M") if fe.created_at else ""
            })

        return AdminSystemHealthResponse(
            api_status="healthy",
            database=database_info,
            ai_provider=ai_provider_info,
            background_queue=background_queue,
            average_ai_latency_ms=average_ai_latency_ms,
            ai_error_rate=ai_error_rate,
            ai_error_count=failed_ai,
            recent_failures=recent_failures
        )
