import os
import uuid
import asyncio
import time
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.space import Space
from app.models.project import Project
from app.models.material import Material, MaterialStatus
from app.models.activity_event import ActivityEventType
from app.services.project_service import ProjectService
from app.services.activity_service import ActivityService
from app.services.pdf_service import PDFService
from app.services.ai_service import AIService
from app.models.document_chunk import DocumentChunk

def process_material_background_task(material_id: int, user_id: int, project_id: int):
    """
    Background worker task for processing material:
    1. Status -> processing
    2. Extract text from PDF preserving page numbers
    3. Split into overlapping chunks
    4. Generate embeddings and store in database
    5. Status -> ready (or failed with error message)
    """
    db = SessionLocal()
    material = None
    try:
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            return

        # Transition 1: processing
        material.status = MaterialStatus.PROCESSING.value
        material.error_message = None
        material.updated_at = datetime.now(timezone.utc)
        db.commit()

        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project_id,
            event_type=ActivityEventType.MATERIAL_PROCESSING_STARTED.value,
            metadata={"material_id": material.id, "filename": material.filename}
        )

        if not os.path.exists(material.file_path):
            raise FileNotFoundError(f"File not found on disk: {material.file_path}")

        file_size = os.path.getsize(material.file_path)
        if file_size == 0:
            raise ValueError("Uploaded file is empty.")

        # 2. Extract text per page
        pages_data = PDFService.extract_text_with_pages(material.file_path)

        # 3. Chunk text preserving page numbers
        chunks_data = PDFService.chunk_document(pages_data, chunk_size=700, chunk_overlap=100)

        # 4. Extract visual elements (tables, diagrams, charts, figures, scanned pages)
        visual_chunks = PDFService.extract_visual_elements(
            file_path=material.file_path,
            pages_data=pages_data,
            material_id=material.id
        )

        all_chunks = []
        global_idx = 0
        for c in chunks_data:
            all_chunks.append({
                "chunk_text": c["chunk_text"],
                "page_number": c["page_number"],
                "chunk_index": global_idx,
                "chunk_type": "text",
                "metadata_json": None
            })
            global_idx += 1

        for vc in visual_chunks:
            all_chunks.append({
                "chunk_text": vc["chunk_text"],
                "page_number": vc["page_number"],
                "chunk_index": global_idx,
                "chunk_type": vc.get("chunk_type", "figure"),
                "metadata_json": vc.get("metadata_json")
            })
            global_idx += 1

        # 5. Generate embeddings for all chunks
        chunk_texts = [c["chunk_text"] for c in all_chunks]
        embeddings = AIService.get_embeddings(chunk_texts) if chunk_texts else []

        # 6. Clear any prior chunks for this material
        db.query(DocumentChunk).filter(DocumentChunk.material_id == material.id).delete()

        # 7. Save chunks to database
        for idx, c in enumerate(all_chunks):
            doc_chunk = DocumentChunk(
                material_id=material.id,
                project_id=project_id,
                chunk_text=c["chunk_text"],
                page_number=c["page_number"],
                chunk_index=c["chunk_index"],
                chunk_type=c.get("chunk_type", "text"),
                metadata_json=c.get("metadata_json"),
                embedding=embeddings[idx] if idx < len(embeddings) else None,
                created_at=datetime.now(timezone.utc)
            )
            db.add(doc_chunk)

        # Transition 2: ready
        material.status = MaterialStatus.READY.value
        material.error_message = None
        material.updated_at = datetime.now(timezone.utc)
        db.commit()

        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project_id,
            event_type=ActivityEventType.MATERIAL_PROCESSED.value,
            metadata={
                "material_id": material.id,
                "filename": material.filename,
                "file_size": file_size,
                "chunk_count": len(chunks_data),
                "page_count": len(pages_data)
            }
        )

    except Exception as exc:
        if material:
            error_text = str(exc)
            material.status = MaterialStatus.FAILED.value
            material.error_message = error_text
            material.updated_at = datetime.now(timezone.utc)
            db.commit()

            ActivityService.log_activity(
                db=db,
                user_id=user_id,
                project_id=project_id,
                event_type=ActivityEventType.MATERIAL_PROCESSING_FAILED.value,
                metadata={
                    "material_id": material.id,
                    "filename": material.filename,
                    "error": error_text
                }
            )
    finally:
        db.close()



class MaterialService:
    @staticmethod
    async def upload_material(
        db: Session,
        project_id: int,
        user_id: int,
        file: UploadFile,
        background_tasks: BackgroundTasks
    ) -> Material:
        # Verify project exists and belongs to user
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        # 1. Check filename extension
        filename = file.filename or "document.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported. File must have a .pdf extension."
            )

        # 2. Check Content-Type header if provided
        if file.content_type and file.content_type not in ["application/pdf", "application/x-pdf", "application/octet-stream"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid content type: {file.content_type}. Only PDF files are allowed."
            )

        # 3. Read file contents and check magic bytes (%PDF-)
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )
        
        if not contents.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. The file is not a valid PDF document."
            )

        # 4. Save file safely
        clean_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        unique_name = f"{uuid.uuid4().hex}_{clean_filename}"
        saved_path = os.path.join(settings.UPLOAD_DIR, unique_name)

        with open(saved_path, "wb") as f:
            f.write(contents)

        # 5. Create Material DB record
        material = Material(
            project_id=project.id,
            filename=filename,
            file_path=saved_path,
            status=MaterialStatus.QUEUED.value
        )
        db.add(material)
        db.commit()
        db.refresh(material)

        # 6. Log activity: MATERIAL_UPLOADED
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.MATERIAL_UPLOADED.value,
            metadata={
                "material_id": material.id,
                "filename": material.filename,
                "project_name": project.name
            }
        )

        # 7. Queue background processing
        background_tasks.add_task(
            process_material_background_task,
            material_id=material.id,
            user_id=user_id,
            project_id=project.id
        )

        return material

    @staticmethod
    def get_project_materials(db: Session, project_id: int, user_id: int) -> List[Material]:
        # Validate project belongs to user
        ProjectService.get_project_by_id(db, project_id, user_id)

        return (
            db.query(Material)
            .filter(Material.project_id == project_id)
            .order_by(Material.created_at.desc())
            .all()
        )

    @staticmethod
    def get_material_by_id(db: Session, material_id: int, user_id: int) -> Material:
        material = (
            db.query(Material)
            .join(Project, Material.project_id == Project.id)
            .join(Space, Project.space_id == Space.id)
            .filter(Material.id == material_id, Space.user_id == user_id)
            .first()
        )
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found or unauthorized."
            )
        return material

    @staticmethod
    def delete_material(db: Session, project_id: int, material_id: int, user_id: int) -> dict:
        # Validate project belongs to user
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        material = db.query(Material).filter(
            Material.id == material_id,
            Material.project_id == project.id
        ).first()

        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found in this project."
            )

        filename = material.filename
        file_path = material.file_path

        # 1. Remove physical file from disk
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[MaterialService] Warning: Failed to remove file {file_path}: {e}")

        # 2. Delete all document chunks and embeddings associated with this material
        db.query(DocumentChunk).filter(DocumentChunk.material_id == material.id).delete()

        # 3. Delete material record
        db.delete(material)

        # 4. Log activity event MATERIAL_DELETED
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.MATERIAL_DELETED.value,
            metadata={
                "material_id": material_id,
                "filename": filename,
                "project_name": project.name
            }
        )

        db.commit()
        return {"message": "Material deleted successfully", "material_id": material_id}

    @staticmethod
    async def replace_material(
        db: Session,
        project_id: int,
        material_id: int,
        user_id: int,
        file: UploadFile,
        background_tasks: BackgroundTasks
    ) -> Material:
        # Validate project belongs to user
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        material = db.query(Material).filter(
            Material.id == material_id,
            Material.project_id == project.id
        ).first()

        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found in this project."
            )

        # 1. Validate PDF extension
        filename = file.filename or "document.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported. File must have a .pdf extension."
            )

        # 2. Validate Content-Type header if provided
        if file.content_type and file.content_type not in ["application/pdf", "application/x-pdf", "application/octet-stream"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid content type: {file.content_type}. Only PDF files are allowed."
            )

        # 3. Validate content non-empty and starts with %PDF-
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        if not contents.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. The file is not a valid PDF document."
            )

        # 4. Remove old physical file from disk
        old_file_path = material.file_path
        if old_file_path and os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except Exception as e:
                print(f"[MaterialService] Warning: Failed to remove old file {old_file_path}: {e}")

        # 5. IMMEDIATELY invalidate/delete old chunks & embeddings so AI Tutor does not use stale content
        db.query(DocumentChunk).filter(DocumentChunk.material_id == material.id).delete()

        # 6. Save new file to disk
        clean_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        unique_name = f"{uuid.uuid4().hex}_{clean_filename}"
        new_saved_path = os.path.join(settings.UPLOAD_DIR, unique_name)

        with open(new_saved_path, "wb") as f:
            f.write(contents)

        # 7. Update Material record
        material.filename = filename
        material.file_path = new_saved_path
        material.status = MaterialStatus.QUEUED.value
        material.error_message = None
        material.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(material)

        # 8. Log activity event MATERIAL_REPLACED
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.MATERIAL_REPLACED.value,
            metadata={
                "material_id": material.id,
                "filename": material.filename,
                "project_name": project.name
            }
        )

        # 9. Queue background processing for new file
        background_tasks.add_task(
            process_material_background_task,
            material_id=material.id,
            user_id=user_id,
            project_id=project.id
        )

        return material
