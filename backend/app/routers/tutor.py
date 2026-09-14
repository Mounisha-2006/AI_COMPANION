from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.tutor import TutorChatRequest, TutorChatResponse, MessageResponse
from app.services.tutor_service import TutorService
from app.routers.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/tutor", tags=["AI Tutor"])

@router.post("/chat", response_model=TutorChatResponse)
def tutor_chat(
    project_id: int,
    request: TutorChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ask a question to the AI Tutor for the given project.
    Retrieves project-scoped context chunks, generates a grounded answer with citations,
    and records the conversation history.
    """
    return TutorService.chat(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        user_message=request.message
    )

@router.get("/history", response_model=List[MessageResponse])
def get_tutor_history(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve prior chat conversation messages and source citations for this project.
    """
    return TutorService.get_history(
        db=db,
        project_id=project_id,
        user_id=current_user.id
    )

@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_tutor_history(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear the AI Tutor conversation history for this project.
    """
    TutorService.clear_history(
        db=db,
        project_id=project_id,
        user_id=current_user.id
    )
    return None
