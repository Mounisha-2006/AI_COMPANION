from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    space_id = Column(Integer, ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    learning_goal = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    space = relationship("Space", back_populates="projects")
    materials = relationship("Material", back_populates="project", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="project", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")
    activity_events = relationship("ActivityEvent", back_populates="project", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="project", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="project", cascade="all, delete-orphan")
    concept_masteries = relationship("ConceptMastery", back_populates="project", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="project", cascade="all, delete-orphan")

