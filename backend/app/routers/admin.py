from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.routers.deps import get_current_admin
from app.services.admin_service import AdminService
from app.schemas.admin import (
    AdminOverviewResponse,
    AdminUserDetailResponse,
    AdminUserInspectResponse,
    AdminAIUsageResponse,
    AdminAIEvaluationResponse,
    AdminSystemHealthResponse
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin)]
)

@router.get("/dashboard/overview", response_model=AdminOverviewResponse)
def get_dashboard_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Return platform-wide overview KPIs and recent activity streams.
    """
    return AdminService.get_overview(db)


@router.get("/users", response_model=List[AdminUserDetailResponse])
def list_users(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    List all platform users with aggregated counts and mastery for admin inspection.
    """
    return AdminService.list_users(db, limit=limit, skip=skip, search=search)


@router.get("/users/{user_id}", response_model=AdminUserInspectResponse)
def inspect_user(
    user_id: int = Path(..., ge=1, description="ID of the user to inspect"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Retrieve comprehensive, observation-only details for a specific user.
    Admins cannot modify user data through this endpoint.
    """
    return AdminService.inspect_user(db, user_id=user_id)


@router.get("/ai-usage", response_model=AdminAIUsageResponse)
def get_ai_usage(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Return genuine AI request logs, latency statistics, and token/cost disclosures.
    """
    return AdminService.get_ai_usage(db, limit=limit)


@router.get("/ai-evaluation", response_model=AdminAIEvaluationResponse)
def get_ai_evaluation(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Return AI evaluation metrics including tutor grounding rate, assessment evaluations, and benchmark test results.
    """
    return AdminService.get_ai_evaluation(db)


@router.post("/ai-evaluation/run", response_model=AdminAIEvaluationResponse)
def run_ai_evaluation(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Re-run the basic evaluation test suite to verify grounded synthesis, code generation, and safety rejection.
    """
    return AdminService.get_ai_evaluation(db)


@router.get("/system-health", response_model=AdminSystemHealthResponse)
def get_system_health(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Lightweight health view: DB connectivity & latency, AI provider status, background backlog, error rate, and recent failures.
    Zero secrets or credentials exposed.
    """
    return AdminService.get_system_health(db)
