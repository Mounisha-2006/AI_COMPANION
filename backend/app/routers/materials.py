from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.material import MaterialResponse
from app.services.material_service import MaterialService
from app.routers.deps import get_current_user

router = APIRouter(tags=["Materials"])

@router.post("/projects/{project_id}/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def upload_material(
    project_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    """
    Upload a PDF material to a project.
    Validates PDF format, stores the file safely, saves Material in 'queued' state,
    and dispatches a background task for processing.
    """
    return await MaterialService.upload_material(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        file=file,
        background_tasks=background_tasks
    )

@router.get("/projects/{project_id}/materials", response_model=List[MaterialResponse])
def get_project_materials(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all materials uploaded to a project.
    Ensures that the project belongs to the authenticated user.
    """
    return MaterialService.get_project_materials(
        db=db, project_id=project_id, user_id=current_user.id
    )

@router.get("/materials/{material_id}", response_model=MaterialResponse)
@router.get("/projects/{project_id}/materials/{material_id}", response_model=MaterialResponse)
def get_material(
    material_id: int,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single material by ID (for polling processing status).
    Ensures ownership by verifying project space user.
    """
    return MaterialService.get_material_by_id(
        db=db, material_id=material_id, user_id=current_user.id
    )

@router.delete("/projects/{project_id}/materials/{material_id}")
def delete_material(
    project_id: int,
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a material from a project.
    Deletes the material record, removes physical file from disk, deletes all chunks and embeddings,
    and logs MATERIAL_DELETED activity.
    """
    return MaterialService.delete_material(
        db=db, project_id=project_id, material_id=material_id, user_id=current_user.id
    )

@router.put("/projects/{project_id}/materials/{material_id}/replace", response_model=MaterialResponse)
@router.post("/projects/{project_id}/materials/{material_id}/replace", response_model=MaterialResponse)
async def replace_material(
    project_id: int,
    material_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Replace an existing material with a new PDF document.
    Removes old physical file and chunks immediately, sets status to 'queued',
    logs MATERIAL_REPLACED, and schedules background processing.
    """
    return await MaterialService.replace_material(
        db=db,
        project_id=project_id,
        material_id=material_id,
        user_id=current_user.id,
        file=file,
        background_tasks=background_tasks
    )
