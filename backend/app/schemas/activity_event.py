from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

class ActivityEventResponse(BaseModel):
    id: int
    user_id: int
    project_id: Optional[int] = None
    event_type: str
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="metadata_json", serialization_alias="metadata")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

