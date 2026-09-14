from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    project_id: int
    concept: str
    reason: str
    recommendation: str
    action_type: str
    priority: str
    created_at: datetime
    completed_at: Optional[datetime] = None

class RecommendationCompleteResponse(BaseModel):
    message: str
    recommendation: RecommendationOut

class ProjectRecommendationsResponse(BaseModel):
    project_id: int
    next_action: Optional[RecommendationOut] = None
    recommendations: List[RecommendationOut]
    total_count: int
    pending_count: int
