import re
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.quiz import Quiz, QuizQuestion, QuizAnswer, QuizStatus, QuestionDifficulty
from app.models.material import Material, MaterialStatus
from app.models.document_chunk import DocumentChunk
from app.models.activity_event import ActivityEventType
from app.services.project_service import ProjectService
from app.services.activity_service import ActivityService
from app.services.ai_service import AIService
from app.schemas.quiz import (
    QuizQuestionOut,
    QuizStartResponse,
    AnswerSubmitResponse,
    QuizDetailResponse,
    QuizSummary,
    QuizAnswerDetail,
)

class QuizService:
    @staticmethod
    def start_quiz(
        db: Session,
        project_id: int,
        user_id: int,
        total_questions: int = 5,
        force_new: bool = False
    ) -> QuizStartResponse:
        # 1. Verify project exists and belongs to user
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        # Check for in-progress quiz resumption
        if not force_new:
            active_quiz = (
                db.query(Quiz)
                .filter(
                    Quiz.project_id == project.id,
                    Quiz.user_id == user_id,
                    Quiz.status == QuizStatus.IN_PROGRESS.value
                )
                .order_by(Quiz.started_at.desc(), Quiz.id.desc())
                .first()
            )
            if active_quiz:
                answered_q_ids = set(
                    r[0] for r in db.query(QuizAnswer.question_id).filter(QuizAnswer.quiz_id == active_quiz.id).all()
                )
                unanswered_q = (
                    db.query(QuizQuestion)
                    .filter(
                        QuizQuestion.quiz_id == active_quiz.id,
                        ~QuizQuestion.id.in_(answered_q_ids) if answered_q_ids else True
                    )
                    .order_by(QuizQuestion.order.asc())
                    .first()
                )
                if unanswered_q:
                    current_q_out = QuizQuestionOut(
                        id=unanswered_q.id,
                        concept=unanswered_q.concept,
                        difficulty=unanswered_q.difficulty,
                        question_type=unanswered_q.question_type,
                        question_text=unanswered_q.question_text,
                        options=unanswered_q.options,
                        order=unanswered_q.order,
                        source_metadata=unanswered_q.source_metadata
                    )
                    return QuizStartResponse(
                        id=active_quiz.id,
                        project_id=active_quiz.project_id,
                        status=active_quiz.status,
                        total_questions=active_quiz.total_questions,
                        score=active_quiz.score,
                        started_at=active_quiz.started_at,
                        current_question=current_q_out
                    )
                else:
                    # All questions in active quiz were answered, mark completed
                    active_quiz.status = QuizStatus.COMPLETED.value
                    active_quiz.completed_at = datetime.now(timezone.utc)
                    db.commit()

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
                detail="No processed materials available in this project to generate a quiz. Please upload a PDF and wait for processing to complete."
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

        # 3. Gather adaptive context (weak concepts and prior questions)
        from app.models.mastery import ConceptMastery
        masteries = db.query(ConceptMastery).filter(
            ConceptMastery.project_id == project.id,
            ConceptMastery.user_id == user_id
        ).all()
        weak_concepts = [
            m.concept for m in masteries
            if m.mastery_score < 65.0 or (getattr(m, 'recent_mistakes_count', getattr(m, 'recent_mistakes', 0)) or 0) > 0
        ]

        existing_q_rows = (
            db.query(QuizQuestion.question_text)
            .filter(QuizQuestion.project_id == project.id)
            .all()
        )
        existing_q_texts = [r[0] for r in existing_q_rows]

        # Generate grounded, randomized, quality-validated questions
        t0 = time.time()
        generated_questions = AIService.generate_quiz_questions(
            context_chunks=context_chunks,
            num_questions=total_questions,
            weak_concepts=weak_concepts,
            existing_questions=existing_q_texts
        )
        lat_ms = int((time.time() - t0) * 1000)
        AIService.log_ai_usage(
            db=db,
            user_id=user_id,
            project_id=project.id,
            feature="quiz_generation",
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
                detail="Could not generate quiz questions from the project materials."
            )

        # 4. Create Quiz in database
        quiz = Quiz(
            project_id=project.id,
            user_id=user_id,
            status=QuizStatus.IN_PROGRESS.value,
            total_questions=len(generated_questions),
            score=0,
            started_at=datetime.now(timezone.utc)
        )
        db.add(quiz)
        db.flush()

        # 5. Save Quiz Questions
        saved_questions = []
        for idx, q in enumerate(generated_questions):
            quiz_q = QuizQuestion(
                quiz_id=quiz.id,
                project_id=project.id,
                concept=q.get("concept", "Core Concept"),
                question_type=q.get("question_type", "mcq"),
                difficulty=q.get("difficulty", QuestionDifficulty.MEDIUM.value),
                question_text=q["question_text"],
                options=q["options"],
                correct_answer=q["correct_answer"],
                source_metadata=q.get("source_metadata"),
                order=idx + 1
            )
            db.add(quiz_q)
            saved_questions.append(quiz_q)

        db.commit()
        db.refresh(quiz)

        # 6. Log Activity: QUIZ_STARTED
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.QUIZ_STARTED.value,
            metadata={
                "quiz_id": quiz.id,
                "total_questions": quiz.total_questions,
                "project_name": project.name
            }
        )

        first_q = saved_questions[0] if saved_questions else None
        current_q_out = None
        if first_q:
            current_q_out = QuizQuestionOut(
                id=first_q.id,
                concept=first_q.concept,
                difficulty=first_q.difficulty,
                question_type=first_q.question_type,
                question_text=first_q.question_text,
                options=first_q.options,
                order=first_q.order,
                source_metadata=first_q.source_metadata
            )

        return QuizStartResponse(
            id=quiz.id,
            project_id=quiz.project_id,
            status=quiz.status,
            total_questions=quiz.total_questions,
            score=quiz.score,
            started_at=quiz.started_at,
            current_question=current_q_out
        )

    @staticmethod
    def submit_answer(
        db: Session,
        project_id: int,
        quiz_id: int,
        question_id: int,
        user_id: int,
        answer_text: str
    ) -> AnswerSubmitResponse:
        # Validate project belongs to user
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        # Retrieve Quiz
        quiz = (
            db.query(Quiz)
            .filter(Quiz.id == quiz_id, Quiz.project_id == project.id, Quiz.user_id == user_id)
            .first()
        )
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found."
            )

        if quiz.status == QuizStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This quiz is already completed."
            )

        # Retrieve Question
        question = (
            db.query(QuizQuestion)
            .filter(QuizQuestion.id == question_id, QuizQuestion.quiz_id == quiz.id)
            .first()
        )
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found in this quiz."
            )

        # Check if already answered
        existing_answer = (
            db.query(QuizAnswer)
            .filter(QuizAnswer.quiz_id == quiz.id, QuizAnswer.question_id == question.id)
            .first()
        )
        if existing_answer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This question has already been answered."
            )

        # Evaluate correctness
        def _normalize(s: str) -> str:
            s = s.strip().lower()
            s = re.sub(r'^(?:[a-d]\s*[\.\)\:\-]\s*|\([a-d]\)\s*)', '', s)
            return s.strip().strip('"\'').rstrip('.').strip()

        clean_user_answer = answer_text.strip().lower()
        clean_correct_answer = question.correct_answer.strip().lower()

        is_correct = (_normalize(clean_user_answer) == _normalize(clean_correct_answer))

        if not is_correct and question.options:
            norm_correct = _normalize(clean_correct_answer)
            # Check letter choice ('a', 'b', 'c', 'd')
            letter_map = {'a': 0, 'b': 1, 'c': 2, 'd': 3}
            if clean_user_answer in letter_map:
                idx = letter_map[clean_user_answer]
                if 0 <= idx < len(question.options) and _normalize(question.options[idx]) == norm_correct:
                    is_correct = True
            elif clean_user_answer.isdigit():
                idx = int(clean_user_answer)
                if 0 <= idx < len(question.options) and _normalize(question.options[idx]) == norm_correct:
                    is_correct = True

        # Build grounded feedback
        source_meta = question.source_metadata or {}
        fn = source_meta.get("filename", "study material")
        pg = source_meta.get("page", 1)

        if is_correct:
            feedback = f"✓ Correct! Verified in {fn} (Page {pg})."
        else:
            feedback = f"✗ Incorrect. The correct answer is: \"{question.correct_answer}\". (Reference: {fn}, Page {pg})"

        # Record Answer
        answer_record = QuizAnswer(
            quiz_id=quiz.id,
            question_id=question.id,
            user_id=user_id,
            answer_text=answer_text.strip(),
            is_correct=is_correct,
            feedback=feedback,
            created_at=datetime.now(timezone.utc)
        )
        db.add(answer_record)

        if is_correct:
            quiz.score += 1

        # Activity: QUESTION_ANSWERED
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.QUESTION_ANSWERED.value,
            metadata={
                "quiz_id": quiz.id,
                "question_id": question.id,
                "concept": question.concept,
                "is_correct": is_correct
            }
        )

        # Update Concept Mastery from Quiz Evidence
        from app.services.mastery_service import MasteryService
        MasteryService.record_evidence(
            db=db,
            user_id=user_id,
            project_id=project.id,
            concept=question.concept,
            score=100.0 if is_correct else 0.0,
            source="quiz"
        )

        db.flush()

        # Get all answered question IDs so far
        all_answers = db.query(QuizAnswer).filter(QuizAnswer.quiz_id == quiz.id).all()
        answered_ids = {a.question_id for a in all_answers}
        total_answered = len(answered_ids)
        is_completed = (total_answered >= quiz.total_questions)

        # Adaptive selection for next question
        next_question_out = None
        summary_out = None

        all_questions = (
            db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == quiz.id)
            .order_by(QuizQuestion.order.asc())
            .all()
        )
        unanswered = [q for q in all_questions if q.id not in answered_ids]

        if unanswered and not is_completed:
            # Adaptive logic:
            # If user got the question wrong -> prioritize same concept or lower difficulty (easy/medium)
            # If user got the question right -> prioritize higher difficulty or new concept
            if not is_correct:
                # Try finding an unanswered question on the same concept first
                same_concept = [q for q in unanswered if q.concept == question.concept]
                if same_concept:
                    chosen = same_concept[0]
                else:
                    # Choose easiest available
                    diff_order = {"easy": 0, "medium": 1, "hard": 2}
                    chosen = min(unanswered, key=lambda q: diff_order.get(q.difficulty, 1))
            else:
                # Progress to different concept or higher difficulty
                diff_order = {"easy": 2, "medium": 1, "hard": 0}
                different_concept = [q for q in unanswered if q.concept != question.concept]
                candidates = different_concept if different_concept else unanswered
                chosen = min(candidates, key=lambda q: diff_order.get(q.difficulty, 1))

            next_question_out = QuizQuestionOut(
                id=chosen.id,
                concept=chosen.concept,
                difficulty=chosen.difficulty,
                question_type=chosen.question_type,
                question_text=chosen.question_text,
                options=chosen.options,
                order=chosen.order,
                source_metadata=chosen.source_metadata
            )
        else:
            is_completed = True

        if is_completed:
            quiz.status = QuizStatus.COMPLETED.value
            quiz.completed_at = datetime.now(timezone.utc)

            # Identify weak concepts
            question_map = {q.id: q for q in all_questions}
            weak_concepts = []
            for a in all_answers:
                if not a.is_correct and a.question_id in question_map:
                    concept_name = question_map[a.question_id].concept
                    if concept_name not in weak_concepts:
                        weak_concepts.append(concept_name)

            percentage = round((quiz.score / quiz.total_questions) * 100, 1) if quiz.total_questions > 0 else 0.0

            summary_out = QuizSummary(
                score=quiz.score,
                total_questions=quiz.total_questions,
                percentage=percentage,
                weak_concepts=weak_concepts,
                status=quiz.status
            )

            # Activity: QUIZ_COMPLETED
            ActivityService.log_activity(
                db=db,
                user_id=user_id,
                project_id=project.id,
                event_type=ActivityEventType.QUIZ_COMPLETED.value,
                metadata={
                    "quiz_id": quiz.id,
                    "score": quiz.score,
                    "total_questions": quiz.total_questions,
                    "percentage": percentage,
                    "weak_concepts": weak_concepts
                }
            )

        db.commit()
        db.refresh(quiz)

        return AnswerSubmitResponse(
            quiz_id=quiz.id,
            question_id=question.id,
            is_correct=is_correct,
            correct_answer=question.correct_answer,
            feedback=feedback,
            current_score=quiz.score,
            total_answered=total_answered,
            total_questions=quiz.total_questions,
            is_completed=is_completed,
            next_question=next_question_out,
            summary=summary_out
        )

    @staticmethod
    def get_quiz(
        db: Session,
        project_id: int,
        quiz_id: int,
        user_id: int
    ) -> QuizDetailResponse:
        # Verify project belongs to user
        project = ProjectService.get_project_by_id(db, project_id, user_id)

        quiz = (
            db.query(Quiz)
            .filter(Quiz.id == quiz_id, Quiz.project_id == project.id, Quiz.user_id == user_id)
            .first()
        )
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found."
            )

        all_questions = (
            db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == quiz.id)
            .order_by(QuizQuestion.order.asc())
            .all()
        )
        all_answers = (
            db.query(QuizAnswer)
            .filter(QuizAnswer.quiz_id == quiz.id)
            .order_by(QuizAnswer.created_at.asc())
            .all()
        )

        answered_ids = {a.question_id for a in all_answers}
        current_question = None
        if quiz.status != QuizStatus.COMPLETED.value:
            for q in all_questions:
                if q.id not in answered_ids:
                    current_question = QuizQuestionOut(
                        id=q.id,
                        concept=q.concept,
                        difficulty=q.difficulty,
                        question_type=q.question_type,
                        question_text=q.question_text,
                        options=q.options,
                        order=q.order,
                        source_metadata=q.source_metadata
                    )
                    break

        summary_out = None
        if quiz.status == QuizStatus.COMPLETED.value:
            question_map = {q.id: q for q in all_questions}
            weak_concepts = []
            for a in all_answers:
                if not a.is_correct and a.question_id in question_map:
                    c = question_map[a.question_id].concept
                    if c not in weak_concepts:
                        weak_concepts.append(c)

            percentage = round((quiz.score / quiz.total_questions) * 100, 1) if quiz.total_questions > 0 else 0.0
            summary_out = QuizSummary(
                score=quiz.score,
                total_questions=quiz.total_questions,
                percentage=percentage,
                weak_concepts=weak_concepts,
                status=quiz.status
            )

        return QuizDetailResponse(
            id=quiz.id,
            project_id=quiz.project_id,
            status=quiz.status,
            total_questions=quiz.total_questions,
            score=quiz.score,
            started_at=quiz.started_at,
            completed_at=quiz.completed_at,
            current_question=current_question,
            answers=[QuizAnswerDetail.model_validate(a) for a in all_answers],
            summary=summary_out
        )

    @staticmethod
    def list_project_quizzes(
        db: Session,
        project_id: int,
        user_id: int
    ) -> List[Quiz]:
        # Verify project belongs to user
        ProjectService.get_project_by_id(db, project_id, user_id)

        return (
            db.query(Quiz)
            .filter(Quiz.project_id == project_id, Quiz.user_id == user_id)
            .order_by(Quiz.created_at.desc())
            .all()
        )
