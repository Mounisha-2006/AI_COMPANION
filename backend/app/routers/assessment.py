from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.assessment import (
    AssessmentStartRequest,
    AssessmentDetailResponse,
    AssessmentSubmitRequest,
    AssessmentResponseOut,
    AssessmentListItem,
)
from app.services.assessment_service import AssessmentService

router = APIRouter(tags=["Assessment"])

@router.post("/projects/{project_id}/assessments/start", response_model=AssessmentDetailResponse, status_code=status.HTTP_201_CREATED)
def start_assessment(
    project_id: int,
    request_data: Optional[AssessmentStartRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start an open-ended conceptual assessment grounded in project materials.
    """
    total_q = request_data.total_questions if request_data and request_data.total_questions else 3
    assessment = AssessmentService.start_assessment(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        total_questions=total_q
    )
    return AssessmentDetailResponse.model_validate(assessment)

@router.post("/projects/{project_id}/assessments/{assessment_id}/submit", response_model=AssessmentResponseOut)
def submit_response(
    project_id: int,
    assessment_id: int,
    request_data: AssessmentSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a learner's open-ended answer for AI evaluation and update concept mastery.
    """
    response_record = AssessmentService.submit_response(
        db=db,
        project_id=project_id,
        assessment_id=assessment_id,
        question_id=request_data.question_id,
        user_id=current_user.id,
        response_text=request_data.response_text
    )
    return AssessmentResponseOut.model_validate(response_record)

@router.get("/projects/{project_id}/assessments/{assessment_id}", response_model=AssessmentDetailResponse)
def get_assessment(
    project_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get full assessment details with questions, submitted responses, and AI evaluations.
    """
    assessment = AssessmentService.get_assessment(
        db=db,
        project_id=project_id,
        assessment_id=assessment_id,
        user_id=current_user.id
    )
    return AssessmentDetailResponse.model_validate(assessment)

@router.get("/projects/{project_id}/assessments", response_model=List[AssessmentListItem])
def list_assessments(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all previous assessments for a project.
    """
    assessments = AssessmentService.list_assessments(
        db=db,
        project_id=project_id,
        user_id=current_user.id
    )
    return [AssessmentListItem.model_validate(a) for a in assessments]
