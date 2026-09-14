from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationOut,
    ProjectRecommendationsResponse,
    RecommendationCompleteResponse
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(
    prefix="/projects/{project_id}/recommendations",
    tags=["Learning Recommendations"]
)

@router.get("", response_model=ProjectRecommendationsResponse, status_code=status.HTTP_200_OK)
def get_project_recommendations(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get contextual learning recommendations answering 'What should I do next?'.
    Prioritizes weak concepts, mistakes, and learning goals.
    """
    return RecommendationService.get_project_recommendations(
        db=db,
        project_id=project_id,
        user_id=current_user.id
    )

@router.post("/generate", response_model=ProjectRecommendationsResponse, status_code=status.HTTP_200_OK)
def refresh_recommendations(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Regenerate/refresh recommendations for the project based on current mastery and evidence.
    """
    RecommendationService.generate_recommendations(
        db=db,
        user_id=current_user.id,
        project_id=project_id
    )
    return RecommendationService.get_project_recommendations(
        db=db,
        project_id=project_id,
        user_id=current_user.id
    )

@router.post("/{recommendation_id}/complete", response_model=RecommendationCompleteResponse, status_code=status.HTTP_200_OK)
def complete_recommendation(
    project_id: int,
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a learning recommendation as completed.
    """
    rec = RecommendationService.complete_recommendation(
        db=db,
        recommendation_id=recommendation_id,
        project_id=project_id,
        user_id=current_user.id
    )
    return RecommendationCompleteResponse(
        message="Recommendation completed successfully",
        recommendation=RecommendationOut.model_validate(rec)
    )
