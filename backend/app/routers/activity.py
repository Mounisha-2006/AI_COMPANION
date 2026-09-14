from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.activity_event import ActivityEventResponse
from app.services.activity_service import ActivityService
from app.services.project_service import ProjectService
from app.routers.deps import get_current_user

router = APIRouter(prefix="/activity", tags=["Activity"])

@router.get("", response_model=List[ActivityEventResponse])
def get_user_activity(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    project_id: Optional[int] = Query(None, description="Filter activities by project ID"),
    event_type: Optional[str] = Query(None, description="Filter activities by event type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recent activity events for the authenticated user, optionally filtered by project or event type.
    """
    if project_id is not None:
        # Validate that project belongs to the user
        ProjectService.get_project_by_id(db, project_id=project_id, user_id=current_user.id)

    return ActivityService.get_user_activities(
        db=db,
        user_id=current_user.id,
        limit=limit,
        skip=skip,
        project_id=project_id,
        event_type=event_type
    )
