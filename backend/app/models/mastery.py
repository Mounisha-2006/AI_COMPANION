from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base

class ConceptMastery(Base):
    __tablename__ = "concept_masteries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    concept = Column(String(255), nullable=False, index=True)
    mastery_score = Column(Float, default=0.0, nullable=False)  # 0.0 to 100.0
    previous_score = Column(Float, default=0.0, nullable=False) # previous score before latest evidence
    confidence = Column(Float, default=0.3, nullable=False)      # 0.0 to 1.0
    evidence_count = Column(Integer, default=1, nullable=False)
    recent_mistakes_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", "concept", name="uq_user_project_concept"),
    )

    # Relationships
    user = relationship("User", back_populates="concept_masteries")
    project = relationship("Project", back_populates="concept_masteries")

    @property
    def recent_mistakes(self) -> int:
        """Compatibility property for recent_mistakes_count."""
        return self.recent_mistakes_count or 0

