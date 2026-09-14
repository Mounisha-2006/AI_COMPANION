import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentResponse, AssessmentStatus
from app.models.material import Material, MaterialStatus
from app.models.document_chunk import DocumentChunk
from app.models.activity_event import ActivityEventType
from app.services.project_service import ProjectService
from app.services.activity_service import ActivityService
from app.services.ai_service import AIService
from app.services.mastery_service import MasteryService

class AssessmentService:
    @staticmethod
    def start_assessment(
        db: Session,
        project_id: int,
        user_id: int,
        total_questions: int = 3
    ) -> Assessment:
        # 1. Validate project exists and belongs to user
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        # 2. Check for ready materials and chunks
        ready_chunks = (
            db.query(DocumentChunk)
            .join(Material, DocumentChunk.material_id == Material.id)
            .filter(DocumentChunk.project_id == project.id, Material.status == MaterialStatus.READY.value)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

        if not ready_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No processed materials available in this project to generate an assessment. Please upload a PDF first."
            )

        context_chunks = [
            {
                "chunk_text": c.chunk_text,
                "page_number": c.page_number,
                "filename": c.material.filename,
                "material_id": c.material_id
            }
            for c in ready_chunks
        ]

        # 3. Generate open-ended conceptual questions
        t0 = time.time()
        generated_questions = AIService.generate_open_ended_questions(
            context_chunks=context_chunks,
            num_questions=total_questions
        )
        lat_ms = int((time.time() - t0) * 1000)
        AIService.log_ai_usage(
            db=db,
            user_id=user_id,
            project_id=project.id,
            feature="assessment_generation",
            model="gemini-1.5-flash" if settings.AI_API_KEY else "local-question-synthesizer",
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            latency_ms=lat_ms,
            success=bool(generated_questions)
        )

        if not generated_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not generate open-ended questions from the project materials."
            )

        # 4. Create Assessment in database
        assessment = Assessment(
            project_id=project.id,
            user_id=user_id,
            title=f"{project.name} Conceptual Assessment",
            status=AssessmentStatus.IN_PROGRESS.value,
            total_questions=len(generated_questions),
            overall_score=None,
            created_at=datetime.now(timezone.utc)
        )
        db.add(assessment)
        db.flush()

        # 5. Save Questions
        for idx, q in enumerate(generated_questions):
            question = AssessmentQuestion(
                assessment_id=assessment.id,
                project_id=project.id,
                question_text=q["question_text"],
                concept=q.get("concept", "Core Concept"),
                difficulty=q.get("difficulty", "medium"),
                source_metadata=q.get("source_metadata"),
                order=idx + 1
            )
            db.add(question)

        db.commit()
        db.refresh(assessment)

        # 6. Log Activity: ASSESSMENT_STARTED
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.ASSESSMENT_STARTED.value,
            metadata={
                "assessment_id": assessment.id,
                "total_questions": assessment.total_questions,
                "project_name": project.name
            }
        )

        return assessment

    @staticmethod
    def submit_response(
        db: Session,
        project_id: int,
        assessment_id: int,
        question_id: int,
        user_id: int,
        response_text: str
    ) -> AssessmentResponse:
        # 1. Validate project belongs to user
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        # 2. Fetch Assessment
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                Assessment.project_id == project.id,
                Assessment.user_id == user_id
            )
            .first()
        )
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found."
            )

        if assessment.status == AssessmentStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This assessment has already been completed."
            )

        # 3. Fetch Question
        question = (
            db.query(AssessmentQuestion)
            .filter(
                AssessmentQuestion.id == question_id,
                AssessmentQuestion.assessment_id == assessment.id
            )
            .first()
        )
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found in this assessment."
            )

        # 4. Check for duplicate response
        existing = (
            db.query(AssessmentResponse)
            .filter(
                AssessmentResponse.assessment_id == assessment.id,
                AssessmentResponse.question_id == question.id
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This question has already been answered."
            )

        # 5. Log Activity: ASSESSMENT_SUBMITTED
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.ASSESSMENT_SUBMITTED.value,
            metadata={
                "assessment_id": assessment.id,
                "question_id": question.id,
                "concept": question.concept
            }
        )

        # 6. Evaluate response using AI
        ready_chunks = (
            db.query(DocumentChunk)
            .join(Material, DocumentChunk.material_id == Material.id)
            .filter(DocumentChunk.project_id == project.id, Material.status == MaterialStatus.READY.value)
            .all()
        )
        context_chunks = [
            {
                "chunk_text": c.chunk_text,
                "page_number": c.page_number,
                "filename": c.material.filename
            }
            for c in ready_chunks
        ]

        t0 = time.time()
        evaluation = AIService.evaluate_open_ended_response(
            question_text=question.question_text,
            concept=question.concept,
            context_chunks=context_chunks,
            user_response=response_text
        )
        lat_ms = int((time.time() - t0) * 1000)
        AIService.log_ai_usage(
            db=db,
            user_id=user_id,
            project_id=assessment.project_id,
            feature="assessment_evaluation",
            model="gemini-1.5-flash" if settings.AI_API_KEY else "local-rubric-evaluator",
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            latency_ms=lat_ms,
            success=True
        )

        # 7. Create AssessmentResponse
        response_record = AssessmentResponse(
            assessment_id=assessment.id,
            question_id=question.id,
            user_id=user_id,
            response_text=response_text.strip(),
            score=evaluation["score"],
            understanding=evaluation["understanding"],
            accuracy=evaluation["accuracy"],
            strengths=evaluation["strengths"],
            missing_concepts=evaluation["missing_concepts"],
            feedback=evaluation["feedback"],
            concepts=evaluation["concepts"],
            created_at=datetime.now(timezone.utc)
        )
        db.add(response_record)
        db.flush()

        # 8. Update Concept Mastery with assessment evidence
        MasteryService.record_evidence(
            db=db,
            user_id=user_id,
            project_id=project.id,
            concept=question.concept,
            score=evaluation["score"],
            source="assessment"
        )

        # 9. Log Activity: ASSESSMENT_EVALUATED
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.ASSESSMENT_EVALUATED.value,
            metadata={
                "assessment_id": assessment.id,
                "question_id": question.id,
                "concept": question.concept,
                "score": evaluation["score"]
            }
        )

        # 10. Check if all questions in assessment are answered
        all_responses = (
            db.query(AssessmentResponse)
            .filter(AssessmentResponse.assessment_id == assessment.id)
            .all()
        )
        if len(all_responses) >= assessment.total_questions:
            assessment.status = AssessmentStatus.COMPLETED.value
            assessment.completed_at = datetime.now(timezone.utc)
            avg_score = sum(r.score for r in all_responses) / len(all_responses)
            assessment.overall_score = round(avg_score, 1)

            # Log Activity: ASSESSMENT_COMPLETED
            ActivityService.log_activity(
                db=db,
                user_id=user_id,
                project_id=project.id,
                event_type=ActivityEventType.ASSESSMENT_COMPLETED.value,
                metadata={
                    "assessment_id": assessment.id,
                    "overall_score": assessment.overall_score,
                    "total_questions": assessment.total_questions
                }
            )

        db.commit()
        db.refresh(response_record)
        return response_record

    @staticmethod
    def get_assessment(
        db: Session,
        project_id: int,
        assessment_id: int,
        user_id: int
    ) -> Assessment:
        # Validate project belongs to user
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                Assessment.project_id == project.id,
                Assessment.user_id == user_id
            )
            .first()
        )
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found."
            )

        return assessment

    @staticmethod
    def list_assessments(
        db: Session,
        project_id: int,
        user_id: int
    ) -> List[Assessment]:
        # Validate project belongs to user
        ProjectService.get_project_by_id(db, project_id, user_id)

        return (
            db.query(Assessment)
            .filter(Assessment.project_id == project_id, Assessment.user_id == user_id)
            .order_by(Assessment.created_at.desc())
            .all()
        )
