from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class QuizStartRequest(BaseModel):
    total_questions: Optional[int] = Field(default=5, ge=1, le=20)
    force_new: Optional[bool] = False

class QuizQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    concept: str
    difficulty: str
    question_type: str
    question_text: str
    options: List[str]
    order: int
    source_metadata: Optional[Dict[str, Any]] = None

class AnswerSubmitRequest(BaseModel):
    question_id: int
    answer_text: str

class QuizAnswerDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer_text: str
    is_correct: bool
    feedback: Optional[str] = None
    created_at: datetime

class QuizSummary(BaseModel):
    score: int
    total_questions: int
    percentage: float
    weak_concepts: List[str]
    status: str

class AnswerSubmitResponse(BaseModel):
    quiz_id: int
    question_id: int
    is_correct: bool
    correct_answer: str
    feedback: str
    current_score: int
    total_answered: int
    total_questions: int
    is_completed: bool
    next_question: Optional[QuizQuestionOut] = None
    summary: Optional[QuizSummary] = None

class QuizStartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    status: str
    total_questions: int
    score: int
    started_at: datetime
    current_question: Optional[QuizQuestionOut] = None

class QuizDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    status: str
    total_questions: int
    score: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    current_question: Optional[QuizQuestionOut] = None
    answers: List[QuizAnswerDetail] = []
    summary: Optional[QuizSummary] = None

class QuizListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    status: str
    total_questions: int
    score: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
