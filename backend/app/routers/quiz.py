from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.quiz import (
    QuizStartRequest,
    QuizStartResponse,
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    QuizDetailResponse,
    QuizListItem,
)
from app.services.quiz_service import QuizService

router = APIRouter(tags=["Quiz"])

@router.post("/projects/{project_id}/quiz/start", response_model=QuizStartResponse, status_code=status.HTTP_201_CREATED)
def start_quiz(
    project_id: int,
    request_data: Optional[QuizStartRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a new adaptive quiz grounded in the project's study materials.
    Returns the quiz instance and the first question.
    """
    total_q = request_data.total_questions if request_data and request_data.total_questions else 5
    force_new = request_data.force_new if request_data and request_data.force_new is not None else False
    return QuizService.start_quiz(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        total_questions=total_q,
        force_new=force_new
    )

@router.post("/projects/{project_id}/quiz/{quiz_id}/answer", response_model=AnswerSubmitResponse)
def submit_answer(
    project_id: int,
    quiz_id: int,
    request_data: AnswerSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit an answer to a quiz question.
    Evaluates correctness, updates score, logs learning evidence,
    and adaptively selects the next question or completes the quiz.
    """
    return QuizService.submit_answer(
        db=db,
        project_id=project_id,
        quiz_id=quiz_id,
        question_id=request_data.question_id,
        user_id=current_user.id,
        answer_text=request_data.answer_text
    )

@router.get("/projects/{project_id}/quiz/{quiz_id}", response_model=QuizDetailResponse)
def get_quiz_detail(
    project_id: int,
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve quiz details, answered questions with citations, active question, and summary.
    """
    return QuizService.get_quiz(
        db=db,
        project_id=project_id,
        quiz_id=quiz_id,
        user_id=current_user.id
    )

@router.get("/projects/{project_id}/quiz", response_model=List[QuizListItem])
@router.get("/projects/{project_id}/quizzes", response_model=List[QuizListItem])
def list_project_quizzes(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all previous quizzes for a project.
    """
    return QuizService.list_project_quizzes(
        db=db,
        project_id=project_id,
        user_id=current_user.id
    )
