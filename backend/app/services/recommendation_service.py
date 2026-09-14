from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.recommendation import Recommendation
from app.models.mastery import ConceptMastery
from app.models.material import Material, MaterialStatus
from app.models.activity_event import ActivityEventType
from app.services.project_service import ProjectService
from app.services.activity_service import ActivityService
from app.schemas.recommendation import RecommendationOut, ProjectRecommendationsResponse

class RecommendationService:
    @classmethod
    def generate_recommendations(
        cls,
        db: Session,
        user_id: int,
        project_id: int
    ) -> List[Recommendation]:
        """
        Generate contextual, grounded recommendations answering 'What should I do next?'.
        Considers weak concepts, recent mistakes, learning goals, available materials,
        and past performance.
        """
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        # 1. Fetch uploaded materials
        materials = (
            db.query(Material)
            .filter(Material.project_id == project_id, Material.status == MaterialStatus.READY.value)
            .all()
        )
        mat_ref = f"the uploaded {materials[0].filename}" if materials else "your uploaded study material"

        # 2. Fetch concept masteries
        masteries = (
            db.query(ConceptMastery)
            .filter(ConceptMastery.project_id == project_id, ConceptMastery.user_id == user_id)
            .order_by(ConceptMastery.mastery_score.asc())
            .all()
        )

        candidates = []

        # Find concepts with mistakes or critical drop
        mistake_concepts = [m for m in masteries if m.recent_mistakes_count > 0 or m.mastery_score < 50.0]
        weak_concepts = [m for m in masteries if m.mastery_score < 65.0 and m not in mistake_concepts]
        improving_concepts = [
            m for m in masteries
            if (round(m.mastery_score - (m.previous_score if m.previous_score is not None else m.mastery_score), 1) >= 3.0)
            and m.mastery_score >= 60.0
        ]

        # Candidate A: Recent mistakes or critical weakness (High Priority)
        for m in mistake_concepts[:2]:
            candidates.append({
                "concept": m.concept,
                "reason": f"Recent difficulties or mistakes detected in {m.concept} (Proficiency: {m.mastery_score}%).",
                "recommendation": f"Review {m.concept.lower()} in {mat_ref} and take a focused practice quiz to reinforce core mechanics.",
                "action_type": "quiz",
                "priority": "high"
            })

        # Candidate B: General weak concepts below target threshold (High Priority)
        for m in weak_concepts[:2]:
            candidates.append({
                "concept": m.concept,
                "reason": f"Concept mastery ({m.mastery_score}%) is below the recommended 65% benchmark.",
                "recommendation": f"Review {m.concept.lower()} in {mat_ref} and complete another short assessment to solidify key concepts.",
                "action_type": "assessment",
                "priority": "high"
            })

        # Candidate C: Improving concepts (Medium Priority)
        for m in improving_concepts[:2]:
            prev = m.previous_score if m.previous_score is not None else m.mastery_score
            diff = round(m.mastery_score - prev, 1)
            diff_str = f"+{diff}%" if diff > 0 else f"{diff}%"
            candidates.append({
                "concept": m.concept,
                "reason": f"Your understanding of {m.concept} has improved ({diff_str}).",
                "recommendation": f"Your understanding of {m.concept} has improved. Try an application-based question to strengthen it.",
                "action_type": "assessment",
                "priority": "medium"
            })

        # Candidate D: Learning goal alignment
        if project.learning_goal and masteries:
            top_concept = masteries[-1].concept  # highest scored concept
            candidates.append({
                "concept": top_concept,
                "reason": f"Targeting your stated learning goal: '{project.learning_goal}'.",
                "recommendation": f"To advance toward your goal '{project.learning_goal}', challenge yourself with advanced questions or ask the AI Tutor about {top_concept.lower()}.",
                "action_type": "chat",
                "priority": "low"
            })

        # Fallback if no masteries exist yet
        if not candidates:
            candidates.append({
                "concept": "Core Concepts",
                "reason": "Initial assessment required to establish learning baseline.",
                "recommendation": f"Begin by reviewing {mat_ref} and starting an open-ended assessment or adaptive quiz.",
                "action_type": "assessment",
                "priority": "high"
            })

        # Persist or update recommendations
        created_or_updated = []
        for cand in candidates:
            # Check for existing uncompleted recommendation for this concept and action_type
            existing = (
                db.query(Recommendation)
                .filter(
                    Recommendation.project_id == project_id,
                    Recommendation.user_id == user_id,
                    Recommendation.concept == cand["concept"],
                    Recommendation.completed_at.is_(None)
                )
                .first()
            )

            if existing:
                existing.reason = cand["reason"]
                existing.recommendation = cand["recommendation"]
                existing.action_type = cand["action_type"]
                existing.priority = cand["priority"]
                created_or_updated.append(existing)
            else:
                rec = Recommendation(
                    user_id=user_id,
                    project_id=project_id,
                    concept=cand["concept"],
                    reason=cand["reason"],
                    recommendation=cand["recommendation"],
                    action_type=cand["action_type"],
                    priority=cand["priority"],
                    created_at=datetime.now(timezone.utc)
                )
                db.add(rec)
                created_or_updated.append(rec)

        db.flush()

        # Log Activity: RECOMMENDATION_GENERATED
        if created_or_updated:
            top_rec = created_or_updated[0]
            ActivityService.log_activity(
                db=db,
                user_id=user_id,
                project_id=project_id,
                event_type=ActivityEventType.RECOMMENDATION_GENERATED.value,
                metadata={
                    "concept": top_rec.concept,
                    "recommendation": top_rec.recommendation,
                    "priority": top_rec.priority,
                    "total_generated": len(created_or_updated)
                }
            )

        return created_or_updated

    @classmethod
    def get_project_recommendations(
        cls,
        db: Session,
        project_id: int,
        user_id: int
    ) -> ProjectRecommendationsResponse:
        ProjectService.get_project_by_id(db, project_id, user_id)

        # Fetch active recommendations
        recs = (
            db.query(Recommendation)
            .filter(Recommendation.project_id == project_id, Recommendation.user_id == user_id)
            .order_by(Recommendation.completed_at.asc(), Recommendation.created_at.desc())
            .all()
        )

        if not recs:
            recs = cls.generate_recommendations(db, user_id, project_id)

        # Sort active recs: 'high' first, then 'medium', then 'low'
        priority_order = {"high": 0, "medium": 1, "low": 2}
        pending_recs = [r for r in recs if r.completed_at is None]
        pending_recs.sort(key=lambda r: priority_order.get(r.priority.lower(), 99))

        next_action_model = pending_recs[0] if pending_recs else (recs[0] if recs else None)
        next_action = RecommendationOut.model_validate(next_action_model) if next_action_model else None

        rec_outs = [RecommendationOut.model_validate(r) for r in recs]

        return ProjectRecommendationsResponse(
            project_id=project_id,
            next_action=next_action,
            recommendations=rec_outs,
            total_count=len(recs),
            pending_count=len(pending_recs)
        )

    @classmethod
    def complete_recommendation(
        cls,
        db: Session,
        recommendation_id: int,
        project_id: int,
        user_id: int
    ) -> Recommendation:
        rec = (
            db.query(Recommendation)
            .filter(
                Recommendation.id == recommendation_id,
                Recommendation.project_id == project_id,
                Recommendation.user_id == user_id
            )
            .first()
        )

        if not rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found"
            )

        rec.completed_at = datetime.now(timezone.utc)
        db.flush()

        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project_id,
            event_type=ActivityEventType.RECOMMENDATION_COMPLETED.value,
            metadata={
                "recommendation_id": rec.id,
                "concept": rec.concept,
                "recommendation": rec.recommendation
            }
        )

        return rec
