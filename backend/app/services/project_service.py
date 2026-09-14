from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.space import Space
from app.models.project import Project
from app.models.material import Material
from app.models.activity_event import ActivityEventType
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.space_service import SpaceService
from app.services.activity_service import ActivityService

class ProjectService:
    @staticmethod
    def create_project(db: Session, space_id: int, user_id: int, project_in: ProjectCreate) -> Project:
        # Verify user owns the space
        space = SpaceService.get_space_by_id(db, space_id, user_id)
        
        project = Project(
            space_id=space.id,
            name=project_in.name.strip(),
            description=project_in.description.strip() if project_in.description else None,
            learning_goal=project_in.learning_goal.strip() if project_in.learning_goal else None
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # Log activity
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.PROJECT_CREATED.value,
            metadata={
                "project_id": project.id,
                "project_name": project.name,
                "space_id": space.id,
                "space_name": space.name
            }
        )

        return project

    @staticmethod
    def get_space_projects(db: Session, space_id: int, user_id: int) -> List[dict]:
        # Verify user owns the space
        SpaceService.get_space_by_id(db, space_id, user_id)
        
        projects = db.query(Project).filter(Project.space_id == space_id).order_by(Project.created_at.desc()).all()
        result = []
        for p in projects:
            mat_count = db.query(func.count(Material.id)).filter(Material.project_id == p.id).scalar() or 0
            result.append({
                "id": p.id,
                "space_id": p.space_id,
                "name": p.name,
                "description": p.description,
                "learning_goal": p.learning_goal,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "material_count": mat_count
            })
        return result

    @staticmethod
    def get_project_by_id(db: Session, project_id: int, user_id: int) -> Project:
        """
        Fetch project ensuring it belongs to a space owned by the user.
        """
        project = (
            db.query(Project)
            .join(Space, Project.space_id == Space.id)
            .filter(Project.id == project_id, Space.user_id == user_id)
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or unauthorized."
            )
        return project

    @staticmethod
    def update_project(db: Session, project_id: int, user_id: int, project_in: ProjectUpdate) -> Project:
        project = ProjectService.get_project_by_id(db, project_id, user_id)
        if project_in.name is not None:
            project.name = project_in.name.strip()
        if project_in.description is not None:
            project.description = project_in.description.strip() if project_in.description else None
        if project_in.learning_goal is not None:
            project.learning_goal = project_in.learning_goal.strip() if project_in.learning_goal else None
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(db: Session, project_id: int, user_id: int) -> None:
        project = ProjectService.get_project_by_id(db, project_id, user_id)
        db.delete(project)
        db.commit()
