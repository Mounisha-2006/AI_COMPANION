from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    learning_goal: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    learning_goal: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: int
    space_id: int
    created_at: datetime
    updated_at: datetime
    material_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

