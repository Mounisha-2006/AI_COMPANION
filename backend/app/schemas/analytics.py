from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.activity_event import ActivityEventResponse

class ActivityTimelinePoint(BaseModel):
    date: str
    count: int
    event_types: Dict[str, int] = {}

class ProjectActivityMetrics(BaseModel):
    learning_sessions: int
    total_events: int
    tutor_questions: int
    quiz_attempts: int
    questions_answered: int
    material_interactions: int

class ProjectPerformanceMetrics(BaseModel):
    quiz_accuracy: float
    current_mastery: float
    concepts_mastered_count: int
    concepts_mastered: List[str]
    concepts_needing_attention_count: int
    concepts_needing_attention: List[str]

class ProjectGrowthMetrics(BaseModel):
    concepts_improving_count: int
    concepts_improving: List[str]
    concepts_stable_count: int
    concepts_stable: List[str]
    concepts_needing_attention_count: int
    concepts_needing_attention: List[str]
    average_assessment_score: Optional[float] = None
    completed_assessments_count: int
    assessment_scores_trend: List[Dict[str, Any]] = []
    activity_over_time: List[ActivityTimelinePoint] = []

class ProjectAIMetrics(BaseModel):
    tutor_interactions: int
    ai_generated_assessments: int
    ai_evaluations: int
    recommendations_generated: int

class ProjectAnalyticsResponse(BaseModel):
    project_id: int
    project_name: str
    activity: ProjectActivityMetrics
    performance: ProjectPerformanceMetrics
    growth: ProjectGrowthMetrics
    ai_activity: ProjectAIMetrics
    recent_activities: List[ActivityEventResponse] = []

    model_config = ConfigDict(from_attributes=True)


class GlobalQuizActivity(BaseModel):
    quizzes_started: int
    quizzes_completed: int
    questions_answered: int
    quiz_accuracy: float

class GlobalAssessmentSummary(BaseModel):
    assessments_started: int
    assessments_completed: int
    average_score: Optional[float] = None
    history: List[Dict[str, Any]] = []

class ProjectSummaryMetric(BaseModel):
    project_id: int
    project_name: str
    space_name: str
    mastery_score: float
    quiz_count: int
    tutor_questions: int
    materials_count: int
    created_at: datetime

class GlobalAnalyticsResponse(BaseModel):
    total_learning_activity: int
    active_days: int
    total_spaces: int
    total_projects: int
    overall_mastery: float
    average_assessment_performance: Optional[float] = None
    concepts_improving: int
    concepts_requiring_attention: int
    tutor_interactions: int
    questions_asked: int
    quiz_activity: GlobalQuizActivity
    ai_generated_feedback: int
    learning_activity_over_time: List[ActivityTimelinePoint] = []
    mastery_over_time: List[Dict[str, Any]] = []
    assessment_performance: GlobalAssessmentSummary
    projects_breakdown: List[ProjectSummaryMetric] = []
    recent_activities: List[ActivityEventResponse] = []

    model_config = ConfigDict(from_attributes=True)
