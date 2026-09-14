from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.mastery import ProjectMasteryResponse
from app.services.mastery_service import MasteryService

router = APIRouter(tags=["Mastery"])

@router.get("/projects/{project_id}/mastery", response_model=ProjectMasteryResponse)
def get_project_mastery(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get estimated concept mastery breakdown and areas needing attention for a project.
    """
    return MasteryService.get_project_mastery(
        db=db,
        project_id=project_id,
        user_id=current_user.id
    )
