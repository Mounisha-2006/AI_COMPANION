from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.activity_event import ActivityEvent, ActivityEventType

class ActivityService:
    @staticmethod
    def log_activity(
        db: Session,
        user_id: int,
        event_type: str,
        project_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ActivityEvent:
        """
        Record a persistent user or system activity event.
        """
        event = ActivityEvent(
            user_id=user_id,
            project_id=project_id,
            event_type=event_type,
            metadata_json=metadata or {}
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_user_activities(
        db: Session,
        user_id: int,
        limit: int = 20,
        skip: int = 0,
        project_id: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> List[ActivityEvent]:
        """
        Fetch recent activity events for the specified user, optionally filtered by project or event type, ordered newest first.
        """
        query = db.query(ActivityEvent).filter(ActivityEvent.user_id == user_id)
        if project_id is not None:
            query = query.filter(ActivityEvent.project_id == project_id)
        if event_type is not None:
            query = query.filter(ActivityEvent.event_type == event_type)
        return (
            query.order_by(ActivityEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_user_activities(
        db: Session,
        user_id: int,
        project_id: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> int:
        """
        Count activity events for the specified user, optionally filtered by project or event type.
        """
        query = db.query(ActivityEvent).filter(ActivityEvent.user_id == user_id)
        if project_id is not None:
            query = query.filter(ActivityEvent.project_id == project_id)
        if event_type is not None:
            query = query.filter(ActivityEvent.event_type == event_type)
        return query.count()
