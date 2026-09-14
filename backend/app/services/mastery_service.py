from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.mastery import ConceptMastery
from app.models.activity_event import ActivityEventType
from app.services.project_service import ProjectService
from app.services.activity_service import ActivityService
from app.schemas.mastery import ConceptMasteryItem, ProjectMasteryResponse

class MasteryService:
    @staticmethod
    def record_evidence(
        db: Session,
        user_id: int,
        project_id: int,
        concept: str,
        score: float,
        source: str = "assessment"
    ) -> ConceptMastery:
        """
        Record learning evidence (from open-ended assessment or adaptive quiz)
        and update estimated mastery for the concept using an explainable strategy.
        """
        clean_concept = concept.strip().capitalize() if concept else "General Concept"

        mastery = (
            db.query(ConceptMastery)
            .filter(
                ConceptMastery.user_id == user_id,
                ConceptMastery.project_id == project_id,
                ConceptMastery.concept == clean_concept
            )
            .first()
        )

        score_clamped = max(0.0, min(100.0, float(score)))

        if not mastery:
            mastery = ConceptMastery(
                user_id=user_id,
                project_id=project_id,
                concept=clean_concept,
                mastery_score=round(score_clamped, 1),
                previous_score=round(score_clamped, 1),
                confidence=0.35,
                evidence_count=1,
                recent_mistakes_count=1 if score_clamped < 60.0 else 0,
                updated_at=datetime.now(timezone.utc)
            )
            db.add(mastery)
        else:
            # Save previous score before applying new evidence
            mastery.previous_score = mastery.mastery_score
            # Weighted moving average: 60% previous mastery + 40% new evidence
            updated_score = (mastery.mastery_score * 0.6) + (score_clamped * 0.4)
            mastery.mastery_score = round(max(0.0, min(100.0, updated_score)), 1)
            mastery.evidence_count += 1
            mastery.confidence = min(1.0, round(0.25 + 0.12 * mastery.evidence_count, 2))

            if score_clamped < 60.0:
                mastery.recent_mistakes_count += 1
            elif score_clamped >= 80.0 and mastery.recent_mistakes_count > 0:
                mastery.recent_mistakes_count -= 1

            mastery.updated_at = datetime.now(timezone.utc)

        db.flush()

        # Log Activity: MASTERY_UPDATED
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project_id,
            event_type=ActivityEventType.MASTERY_UPDATED.value,
            metadata={
                "concept": clean_concept,
                "mastery_score": mastery.mastery_score,
                "confidence": mastery.confidence,
                "evidence_count": mastery.evidence_count,
                "source": source
            }
        )

        # Update project recommendations to close the learning loop
        try:
            from app.services.recommendation_service import RecommendationService
            RecommendationService.generate_recommendations(db, user_id, project_id)
        except Exception:
            pass

        return mastery

    @staticmethod
    def get_project_mastery(
        db: Session,
        project_id: int,
        user_id: int
    ) -> ProjectMasteryResponse:
        # Validate project belongs to user
        ProjectService.get_project_by_id(db, project_id, user_id)

        masteries = (
            db.query(ConceptMastery)
            .filter(ConceptMastery.project_id == project_id, ConceptMastery.user_id == user_id)
            .order_by(ConceptMastery.mastery_score.desc())
            .all()
        )

        # Identify areas needing attention (mastery < 65% or recent mistakes > 0)
        areas_needing_attention = [
            m.concept for m in masteries
            if m.mastery_score < 65.0 or m.recent_mistakes_count > 0
        ]

        return ProjectMasteryResponse(
            project_id=project_id,
            concepts=[ConceptMasteryItem.model_validate(m) for m in masteries],
            areas_needing_attention=areas_needing_attention
        )
