from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.analytics import ProjectAnalyticsResponse, GlobalAnalyticsResponse
from app.services.analytics_service import AnalyticsService
from app.routers.deps import get_current_user

router = APIRouter(tags=["Analytics"])

@router.get(
    "/projects/{project_id}/analytics",
    response_model=ProjectAnalyticsResponse,
    status_code=status.HTTP_200_OK
)
def get_project_analytics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed analytics for a specific project.
    Validates that the project belongs to a space owned by the authenticated user.
    """
    return AnalyticsService.get_project_analytics(
        db=db,
        project_id=project_id,
        user_id=current_user.id
    )

@router.get(
    "/analytics/global",
    response_model=GlobalAnalyticsResponse,
    status_code=status.HTTP_200_OK
)
def get_global_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated learning analytics across all spaces and projects for the authenticated user.
    """
    return AnalyticsService.get_global_analytics(
        db=db,
        user_id=current_user.id
    )

@router.get(
    "/analytics",
    response_model=GlobalAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def get_global_analytics_alias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Alias endpoint for global analytics.
    """
    return AnalyticsService.get_global_analytics(
        db=db,
        user_id=current_user.id
    )
