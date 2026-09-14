from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.activity_event import ActivityEventResponse

class AdminOverviewKPIs(BaseModel):
    total_users: int
    total_spaces: int
    total_projects: int
    total_materials: int
    total_tutor_interactions: int
    total_quizzes: int
    total_assessments: int

class AdminUserSummary(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime
    spaces_count: int
    projects_count: int
    quizzes_count: int
    overall_mastery: float

    model_config = ConfigDict(from_attributes=True)

class AdminProjectSummary(BaseModel):
    id: int
    name: str
    space_name: str
    user_email: str
    materials_count: int
    created_at: datetime

class AdminOverviewResponse(BaseModel):
    kpis: AdminOverviewKPIs
    recent_users: List[AdminUserSummary] = []
    recent_projects: List[AdminProjectSummary] = []
    recent_activity_events: List[ActivityEventResponse] = []
    recent_material_events: List[ActivityEventResponse] = []


class AdminUserDetailResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime
    spaces_count: int
    projects_count: int
    quizzes_count: int
    tutor_questions_count: int
    overall_mastery: float

    model_config = ConfigDict(from_attributes=True)

class AdminUserSpaceItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    projects_count: int
    created_at: datetime

class AdminUserProjectItem(BaseModel):
    id: int
    name: str
    space_name: str
    learning_goal: Optional[str] = None
    materials_count: int
    mastery_score: float
    created_at: datetime

class AdminUserInspectResponse(BaseModel):
    user: AdminUserDetailResponse
    spaces: List[AdminUserSpaceItem] = []
    projects: List[AdminUserProjectItem] = []
    activities: List[ActivityEventResponse] = []
    mastery_breakdown: List[Dict[str, Any]] = []
    completed_assessments: List[Dict[str, Any]] = []
    quiz_accuracy: float
    total_quiz_attempts: int


class AdminAIUsageItem(BaseModel):
    id: int
    user_id: Optional[int] = None
    project_id: Optional[int] = None
    feature: str
    model: Optional[str] = None
    latency_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    success: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AdminAIUsageResponse(BaseModel):
    total_requests: int
    feature_breakdown: Dict[str, int] = {}
    model_breakdown: Dict[str, int] = {}
    latency_stats: Dict[str, Any] = {}
    token_usage: Dict[str, Any] = {}
    estimated_cost: Dict[str, Any] = {}
    error_count: int
    success_rate: float
    recent_requests: List[AdminAIUsageItem] = []


class AIEvaluationBenchmarkItem(BaseModel):
    test_name: str
    category: str
    input_query: str
    status: str
    latency_ms: int
    details: str

class AdminAIEvaluationResponse(BaseModel):
    tutor_evaluation: Dict[str, Any] = {}
    assessment_evaluation: Dict[str, Any] = {}
    ai_errors_count: int
    benchmark_results: List[AIEvaluationBenchmarkItem] = []


class AdminSystemHealthResponse(BaseModel):
    api_status: str
    database: Dict[str, Any] = {}
    ai_provider: Dict[str, Any] = {}
    background_queue: Dict[str, Any] = {}
    average_ai_latency_ms: float
    ai_error_rate: float
    ai_error_count: int
    recent_failures: List[Dict[str, Any]] = []
