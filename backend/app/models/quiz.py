from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base

class QuizStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class QuestionDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default=QuizStatus.IN_PROGRESS.value, nullable=False, index=True)
    total_questions = Column(Integer, default=5, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="quizzes")
    user = relationship("User", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan", order_by="QuizQuestion.order")
    answers = relationship("QuizAnswer", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    concept = Column(String(255), nullable=False, index=True)
    question_type = Column(String(50), default="mcq", nullable=False)
    difficulty = Column(String(50), default=QuestionDifficulty.MEDIUM.value, nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # List of strings e.g. ["A", "B", "C", "D"]
    correct_answer = Column(Text, nullable=False)
    source_metadata = Column(JSON, nullable=True)  # {"filename": "...", "page": 1}
    order = Column(Integer, default=1, nullable=False)

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    project = relationship("Project")
    answers = relationship("QuizAnswer", back_populates="question", cascade="all, delete-orphan")


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    quiz = relationship("Quiz", back_populates="answers")
    question = relationship("QuizQuestion", back_populates="answers")
    user = relationship("User", back_populates="quiz_answers")
