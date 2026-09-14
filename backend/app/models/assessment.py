from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base

class AssessmentStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="Open-Ended Conceptual Assessment", nullable=False)
    status = Column(String(50), default=AssessmentStatus.IN_PROGRESS.value, nullable=False, index=True)
    total_questions = Column(Integer, default=3, nullable=False)
    overall_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="assessments")
    user = relationship("User", back_populates="assessments")
    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentQuestion.order")
    responses = relationship("AssessmentResponse", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    concept = Column(String(255), nullable=False, index=True)
    difficulty = Column(String(50), default="medium", nullable=False)
    source_metadata = Column(JSON, nullable=True)  # {"filename": "...", "page": 1}
    order = Column(Integer, default=1, nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="questions")
    project = relationship("Project")
    responses = relationship("AssessmentResponse", back_populates="question", cascade="all, delete-orphan")


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    response_text = Column(Text, nullable=False)
    score = Column(Integer, nullable=False)  # 0 to 100
    understanding = Column(Text, nullable=True)
    accuracy = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=True)  # list of strings
    missing_concepts = Column(JSON, nullable=True)  # list of strings
    feedback = Column(Text, nullable=True)
    concepts = Column(JSON, nullable=True)  # list of covered concepts
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="responses")
    question = relationship("AssessmentQuestion", back_populates="responses")
    user = relationship("User", back_populates="assessment_responses")
