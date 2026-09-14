from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict

class ConceptMasteryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    concept: str
    mastery_score: float
    confidence: float
    evidence_count: int
    recent_mistakes_count: int
    updated_at: datetime

class ProjectMasteryResponse(BaseModel):
    project_id: int
    concepts: List[ConceptMasteryItem]
    areas_needing_attention: List[str]
