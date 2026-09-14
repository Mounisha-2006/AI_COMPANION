from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class AssessmentStartRequest(BaseModel):
    total_questions: Optional[int] = Field(default=3, ge=1, le=10)

class AssessmentQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_text: str
    concept: str
    difficulty: str
    source_metadata: Optional[Dict[str, Any]] = None
    order: int

class AssessmentSubmitRequest(BaseModel):
    question_id: int
    response_text: str

class AssessmentEvaluationOut(BaseModel):
    score: int
    understanding: str
    accuracy: str
    strengths: List[str]
    missing_concepts: List[str]
    feedback: str
    concepts: List[str]

class AssessmentResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    question_id: int
    response_text: str
    score: int
    understanding: Optional[str] = None
    accuracy: Optional[str] = None
    strengths: Optional[List[str]] = None
    missing_concepts: Optional[List[str]] = None
    feedback: Optional[str] = None
    concepts: Optional[List[str]] = None
    created_at: datetime

class AssessmentDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    status: str
    total_questions: int
    overall_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    questions: List[AssessmentQuestionOut] = []
    responses: List[AssessmentResponseOut] = []

class AssessmentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    status: str
    total_questions: int
    overall_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
