from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MaterialResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    file_path: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


