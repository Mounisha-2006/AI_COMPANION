from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.space import SpaceCreate, SpaceUpdate, SpaceResponse
from app.services.space_service import SpaceService
from app.routers.deps import get_current_user

router = APIRouter(prefix="/spaces", tags=["Spaces"])

@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
def create_space(
    space_in: SpaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new study space for the authenticated user.
    """
    space = SpaceService.create_space(db=db, user_id=current_user.id, space_in=space_in)
    return space

@router.get("", response_model=List[SpaceResponse])
def get_spaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all study spaces owned by the current user.
    """
    return SpaceService.get_user_spaces(db=db, user_id=current_user.id)

@router.get("/{space_id}", response_model=SpaceResponse)
def get_space(
    space_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single study space by ID. Ensures user ownership.
    """
    return SpaceService.get_space_by_id(db=db, space_id=space_id, user_id=current_user.id)

@router.put("/{space_id}", response_model=SpaceResponse)
def update_space(
    space_id: int,
    space_in: SpaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a study space. Ensures user ownership.
    """
    return SpaceService.update_space(
        db=db, space_id=space_id, user_id=current_user.id, space_in=space_in
    )

@router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_space(
    space_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a study space and cascade delete its projects and materials.
    """
    SpaceService.delete_space(db=db, space_id=space_id, user_id=current_user.id)
    return None
