from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.mastery import ConceptMastery
from app.services.project_service import ProjectService
from app.schemas.growth import ConceptGrowthItem, GrowthSummary, ProjectGrowthResponse

class GrowthService:
    @staticmethod
    def classify_status(previous: float, current: float, recent_mistakes: int = 0) -> str:
        """
        Classify concept status into 'Improving', 'Stable', or 'Needs Attention'.
        Follows criteria:
        - Needs Attention: change <= -3.0% OR current < 50.0% OR (current < 60.0% and change < 3.0%) OR (recent_mistakes > 0 and current < 65.0%)
        - Improving: change >= +3.0% and current >= 50.0%
        - Stable: within [-3.0%, +3.0%] and current >= 60.0%
        """
        change = round(current - previous, 1)
        if change <= -3.0 or current < 50.0 or (current < 60.0 and change < 3.0) or (recent_mistakes > 0 and current < 65.0):
            return "Needs Attention"
        elif change >= 3.0:
            return "Improving"
        else:
            return "Stable"

    @classmethod
    def get_project_growth(cls, db: Session, project_id: int, user_id: int) -> ProjectGrowthResponse:
        # Validate project ownership and existence
        ProjectService.get_project_by_id(db, project_id, user_id)

        masteries = (
            db.query(ConceptMastery)
            .filter(ConceptMastery.project_id == project_id, ConceptMastery.user_id == user_id)
            .order_by(ConceptMastery.mastery_score.desc())
            .all()
        )

        growth_items: List[ConceptGrowthItem] = []
        strong_areas: List[str] = []
        weak_areas: List[str] = []
        improving_areas: List[str] = []
        stable_areas: List[str] = []
        areas_requiring_attention: List[str] = []

        total_mastery_sum = 0.0

        for m in masteries:
            curr = round(m.mastery_score, 1)
            prev = round(m.previous_score if m.previous_score is not None else curr, 1)
            # If concept was just created (evidence_count == 1 and previous was unset/0),
            # use previous_score or curr for a sensible baseline
            if m.evidence_count == 1 and m.previous_score == 0.0 and curr > 0.0:
                prev = curr

            change = round(curr - prev, 1)
            status_str = cls.classify_status(prev, curr, m.recent_mistakes_count)

            growth_items.append(
                ConceptGrowthItem(
                    concept=m.concept,
                    previous_mastery=prev,
                    current_mastery=curr,
                    change=change,
                    status=status_str,
                    confidence=round(m.confidence, 2),
                    recent_mistakes=m.recent_mistakes_count
                )
            )

            total_mastery_sum += curr

            if curr >= 75.0:
                strong_areas.append(m.concept)
            if curr < 65.0:
                weak_areas.append(m.concept)

            if status_str == "Improving":
                improving_areas.append(m.concept)
            elif status_str == "Stable":
                stable_areas.append(m.concept)
            elif status_str == "Needs Attention":
                areas_requiring_attention.append(m.concept)

        # Include any weak areas in areas_requiring_attention if not already included
        for w in weak_areas:
            if w not in areas_requiring_attention:
                areas_requiring_attention.append(w)

        overall_progress = round(total_mastery_sum / len(masteries), 1) if masteries else 0.0

        summary = GrowthSummary(
            total_concepts=len(masteries),
            overall_progress=overall_progress,
            strong_areas=strong_areas,
            weak_areas=weak_areas,
            improving_areas=improving_areas,
            stable_areas=stable_areas,
            areas_requiring_attention=areas_requiring_attention
        )

        return ProjectGrowthResponse(
            project_id=project_id,
            overall_progress=overall_progress,
            concepts=growth_items,
            summary=summary
        )
