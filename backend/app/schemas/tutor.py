from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class TutorChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="The question or prompt to ask the AI Tutor")

class TutorSource(BaseModel):
    material_id: int
    filename: str
    page: int
    visual_type: Optional[str] = None

class TutorChatResponse(BaseModel):
    answer: str
    sources: List[TutorSource] = []
    grounded: bool = True

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata_json")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class ConversationResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    messages: List[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
