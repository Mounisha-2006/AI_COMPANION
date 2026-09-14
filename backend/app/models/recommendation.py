from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    concept = Column(String(255), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    action_type = Column(String(50), default="assessment", nullable=False)  # "assessment", "quiz", "review", "chat"
    priority = Column(String(50), default="medium", nullable=False)        # "high", "medium", "low"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="recommendations")
    project = relationship("Project", back_populates="recommendations")
