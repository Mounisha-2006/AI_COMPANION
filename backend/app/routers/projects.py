from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project_service import ProjectService
from app.services.activity_service import ActivityService
from app.models.activity_event import ActivityEventType
from app.routers.deps import get_current_user

router = APIRouter(tags=["Projects"])

@router.post("/spaces/{space_id}/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    space_id: int,
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a project inside the specified space.
    Ensures that the space exists and belongs to the authenticated user.
    """
    return ProjectService.create_project(
        db=db, space_id=space_id, user_id=current_user.id, project_in=project_in
    )

@router.get("/spaces/{space_id}/projects", response_model=List[ProjectResponse])
def get_space_projects(
    space_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all projects belonging to a space.
    Ensures that the space belongs to the authenticated user.
    """
    return ProjectService.get_space_projects(db=db, space_id=space_id, user_id=current_user.id)

@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get project details.
    Ensures that the project belongs to a space owned by the authenticated user.
    """
    project = ProjectService.get_project_by_id(db=db, project_id=project_id, user_id=current_user.id)

    ActivityService.log_activity(
        db=db,
        user_id=current_user.id,
        project_id=project.id,
        event_type=ActivityEventType.PROJECT_ACCESSED.value,
        metadata={"project_name": project.name}
    )

    return project

@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update project details.
    Ensures that the project belongs to a space owned by the authenticated user.
    """
    return ProjectService.update_project(
        db=db, project_id=project_id, user_id=current_user.id, project_in=project_in
    )

@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a project.
    Ensures that the project belongs to a space owned by the authenticated user.
    """
    ProjectService.delete_project(db=db, project_id=project_id, user_id=current_user.id)
    return None
