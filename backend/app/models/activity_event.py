from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base

class ActivityEventType(str, enum.Enum):
    SPACE_CREATED = "SPACE_CREATED"
    PROJECT_CREATED = "PROJECT_CREATED"
    MATERIAL_UPLOADED = "MATERIAL_UPLOADED"
    MATERIAL_PROCESSING_STARTED = "MATERIAL_PROCESSING_STARTED"
    MATERIAL_PROCESSED = "MATERIAL_PROCESSED"
    MATERIAL_PROCESSING_FAILED = "MATERIAL_PROCESSING_FAILED"
    MATERIAL_DELETED = "MATERIAL_DELETED"
    MATERIAL_REPLACED = "MATERIAL_REPLACED"
    QUIZ_STARTED = "QUIZ_STARTED"
    QUESTION_ANSWERED = "QUESTION_ANSWERED"
    QUIZ_COMPLETED = "QUIZ_COMPLETED"
    ASSESSMENT_STARTED = "ASSESSMENT_STARTED"
    ASSESSMENT_SUBMITTED = "ASSESSMENT_SUBMITTED"
    ASSESSMENT_EVALUATED = "ASSESSMENT_EVALUATED"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    MASTERY_UPDATED = "MASTERY_UPDATED"
    RECOMMENDATION_GENERATED = "RECOMMENDATION_GENERATED"
    RECOMMENDATION_COMPLETED = "RECOMMENDATION_COMPLETED"
    TUTOR_QUESTION = "TUTOR_QUESTION"
    TUTOR_CONVERSATION_STARTED = "TUTOR_CONVERSATION_STARTED"
    GROWTH_VIEWED = "GROWTH_VIEWED"
    PROJECT_ACCESSED = "PROJECT_ACCESSED"

class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="activity_events")
    project = relationship("Project", back_populates="activity_events")
