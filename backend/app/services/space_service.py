from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.space import Space
from app.models.project import Project
from app.models.activity_event import ActivityEventType
from app.schemas.space import SpaceCreate, SpaceUpdate
from app.services.activity_service import ActivityService

class SpaceService:
    @staticmethod
    def create_space(db: Session, user_id: int, space_in: SpaceCreate) -> Space:
        space = Space(
            user_id=user_id,
            name=space_in.name.strip(),
            description=space_in.description.strip() if space_in.description else None
        )
        db.add(space)
        db.commit()
        db.refresh(space)

        # Log activity
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            event_type=ActivityEventType.SPACE_CREATED.value,
            metadata={"space_id": space.id, "space_name": space.name}
        )

        return space

    @staticmethod
    def get_user_spaces(db: Session, user_id: int) -> List[dict]:
        """
        Get all spaces belonging to user, populated with project_count.
        """
        spaces = db.query(Space).filter(Space.user_id == user_id).order_by(Space.created_at.desc()).all()
        result = []
        for s in spaces:
            count = db.query(func.count(Project.id)).filter(Project.space_id == s.id).scalar() or 0
            result.append({
                "id": s.id,
                "user_id": s.user_id,
                "name": s.name,
                "description": s.description,
                "created_at": s.created_at,
                "project_count": count
            })
        return result

    @staticmethod
    def get_space_by_id(db: Session, space_id: int, user_id: int) -> Space:
        """
        Fetch space strictly ensuring ownership.
        """
        space = db.query(Space).filter(Space.id == space_id, Space.user_id == user_id).first()
        if not space:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Space not found or unauthorized."
            )
        return space

    @staticmethod
    def update_space(db: Session, space_id: int, user_id: int, space_in: SpaceUpdate) -> Space:
        space = SpaceService.get_space_by_id(db, space_id, user_id)
        if space_in.name is not None:
            space.name = space_in.name.strip()
        if space_in.description is not None:
            space.description = space_in.description.strip() if space_in.description else None
        db.commit()
        db.refresh(space)
        return space

    @staticmethod
    def delete_space(db: Session, space_id: int, user_id: int) -> None:
        space = SpaceService.get_space_by_id(db, space_id, user_id)
        db.delete(space)
        db.commit()
