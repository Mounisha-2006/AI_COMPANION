from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.schemas.growth import ProjectGrowthResponse
from app.services.growth_service import GrowthService
from app.services.activity_service import ActivityService
from app.models.activity_event import ActivityEventType

router = APIRouter(
    prefix="/projects/{project_id}/growth",
    tags=["Growth Analysis"]
)

@router.get("", response_model=ProjectGrowthResponse, status_code=status.HTTP_200_OK)
def get_project_growth(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get concept growth analysis comparing previous mastery with current mastery,
    classifying concepts as Improving, Stable, or Needs Attention, and providing
    aggregated summary metrics.
    """
    result = GrowthService.get_project_growth(
        db=db,
        project_id=project_id,
        user_id=current_user.id
    )

    ActivityService.log_activity(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
        event_type=ActivityEventType.GROWTH_VIEWED.value,
        metadata={"project_id": project_id}
    )

    return result
