from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class ConceptGrowthItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    concept: str
    previous_mastery: float
    current_mastery: float
    change: float
    status: str  # "Improving", "Stable", "Needs Attention"
    confidence: float
    recent_mistakes: int

class GrowthSummary(BaseModel):
    total_concepts: int
    overall_progress: float
    strong_areas: List[str]
    weak_areas: List[str]
    improving_areas: List[str]
    stable_areas: List[str]
    areas_requiring_attention: List[str]

class ProjectGrowthResponse(BaseModel):
    project_id: int
    overall_progress: float
    concepts: List[ConceptGrowthItem]
    summary: GrowthSummary
