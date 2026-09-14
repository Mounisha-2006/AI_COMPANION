from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.conversation import Conversation, Message
from app.models.material import Material, MaterialStatus
from app.models.document_chunk import DocumentChunk
from app.services.project_service import ProjectService
from app.services.retrieval_service import RetrievalService
from app.services.ai_service import AIService
from app.services.activity_service import ActivityService
from app.models.activity_event import ActivityEventType
from app.schemas.tutor import TutorChatResponse, TutorSource, MessageResponse
import logging

logger = logging.getLogger("ai_tutor")

class TutorService:
    @classmethod
    def get_or_create_conversation(cls, db: Session, project_id: int, user_id: int) -> Conversation:
        """
        Find existing active conversation for project or create a new one.
        """
        conv = (
            db.query(Conversation)
            .filter(Conversation.project_id == project_id, Conversation.user_id == user_id)
            .first()
        )
        if not conv:
            conv = Conversation(
                project_id=project_id,
                user_id=user_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)

            ActivityService.log_activity(
                db=db,
                user_id=user_id,
                project_id=project_id,
                event_type=ActivityEventType.TUTOR_CONVERSATION_STARTED.value,
                metadata={"conversation_id": conv.id}
            )
        return conv

    @classmethod
    def chat(
        cls,
        db: Session,
        project_id: int,
        user_id: int,
        user_message: str
    ) -> TutorChatResponse:
        """
        Execute AI Tutor RAG pipeline:
        1. Verify project ownership.
        2. Check for uploaded materials.
        3. Retrieve relevant chunks scoped strictly to this project.
        4. Generate grounded student answer with citations.
        5. Persist conversation history.
        """
        # 1. Verify project ownership
        project = ProjectService.get_project_by_id(db, project_id=project_id, user_id=user_id)

        clean_message = user_message.strip()
        if not clean_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty."
            )

        # 2. Check if project has materials
        materials = db.query(Material).filter(Material.project_id == project.id).all()
        if not materials:
            return TutorChatResponse(
                answer="No study materials have been uploaded to this project yet. Please upload a PDF in the Materials section to begin asking questions.",
                sources=[],
                grounded=False
            )

        # Check if materials are still processing
        ready_materials = [m for m in materials if m.status == MaterialStatus.READY.value]
        if not ready_materials:
            has_processing = any(m.status in [MaterialStatus.QUEUED.value, MaterialStatus.PROCESSING.value] for m in materials)
            if has_processing:
                return TutorChatResponse(
                    answer="Your study materials are currently being processed in the background. Please wait a moment until processing finishes.",
                    sources=[],
                    grounded=False
                )
            else:
                return TutorChatResponse(
                    answer="None of the uploaded materials could be processed successfully. Please verify your PDF file and upload again.",
                    sources=[],
                    grounded=False
                )

        # 3. Retrieve conversation history for context continuity
        conversation = cls.get_or_create_conversation(db, project_id=project.id, user_id=user_id)
        recent_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(6)
            .all()
        )
        recent_messages.reverse()
        conversation_history = [{"role": m.role, "content": m.content} for m in recent_messages]

        # Contextual query resolution for follow-up questions
        retrieval_query = clean_message
        lower_msg = clean_message.lower()
        follow_up_triggers = [
            "give me an example", "give an example", "show an example", "another example",
            "how do i call it", "how do i use it", "how to call it", "how to use it",
            "why is that", "explain it", "tell me more", "what does it do", "give me one",
            "can you give an example", "can you show an example", "example please"
        ]
        is_follow_up = any(t in lower_msg for t in follow_up_triggers)
        if not is_follow_up and len(clean_message.split()) <= 4:
            if any(p in lower_msg.split() for p in ["it", "this", "that", "them", "these", "those"]):
                is_follow_up = True

        if is_follow_up and recent_messages:
            # Find the most recent topic from previous user or assistant message
            for prev_m in reversed(recent_messages):
                prev_text = prev_m.content.lower()
                concepts = ["list", "function", "variable", "dictionary", "range", "loop", "array", "syntax", "indexing", "class", "object", "data type"]
                found_concepts = [c for c in concepts if c in prev_text]
                if found_concepts:
                    retrieval_query = f"{clean_message} {found_concepts[0]}"
                    break

        # 4. Retrieve relevant chunks strictly for this project
        relevant_chunks = RetrievalService.search_project_chunks(
            db=db,
            project_id=project.id,
            user_id=user_id,
            query=retrieval_query,
            top_k=4
        )

        # 5. Generate grounded answer prioritizing project material
        rag_result = AIService.generate_grounded_answer(
            db=db,
            user_id=user_id,
            project_id=project.id,
            question=clean_message,
            context_chunks=relevant_chunks,
            conversation_history=conversation_history
        )

        answer = rag_result["answer"]
        sources = [TutorSource(**s) for s in rag_result.get("sources", [])]
        grounded = rag_result.get("grounded", False)

        # Debug logging
        chunk_ids = [c.get("chunk_id") for c in relevant_chunks]
        retrieved_text_len = sum(len(c.get("chunk_text", "")) for c in relevant_chunks)
        prompt_len = rag_result.get("prompt_length", 0)
        raw_llm = rag_result.get("raw_llm_response", "")
        cit_repr = [s.model_dump() for s in sources]
        
        logger.info(f"[AI Tutor] user question: {clean_message}")
        logger.info(f"[AI Tutor] retrieved chunk IDs: {chunk_ids}")
        logger.info(f"[AI Tutor] retrieved text length: {retrieved_text_len}")
        logger.info(f"[AI Tutor] final LLM prompt/context length: {prompt_len}")
        logger.info(f"[AI Tutor] LLM response: {raw_llm}")
        logger.info(f"[AI Tutor] parsed answer: {answer}")
        logger.info(f"[AI Tutor] citations: {cit_repr}")
        print(f"[AI Tutor DEBUG] Q: '{clean_message}' | Chunks: {chunk_ids} ({retrieved_text_len} chars) | Citations: {cit_repr}")

        # Store user question
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=clean_message,
            created_at=datetime.now(timezone.utc)
        )
        db.add(user_msg)

        # Store assistant response with source metadata
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            metadata_json={
                "sources": [s.model_dump() for s in sources],
                "grounded": grounded
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(assistant_msg)

        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Log Activity: TUTOR_QUESTION
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            project_id=project.id,
            event_type=ActivityEventType.TUTOR_QUESTION.value,
            metadata={
                "question_length": len(clean_message),
                "question_preview": clean_message[:80],
                "grounded": grounded,
                "source_count": len(sources)
            }
        )

        return TutorChatResponse(
            answer=answer,
            sources=sources,
            grounded=grounded
        )

    @classmethod
    def get_history(cls, db: Session, project_id: int, user_id: int) -> List[Dict[str, Any]]:
        """
        Fetch conversation messages for the project.
        """
        ProjectService.get_project_by_id(db, project_id=project_id, user_id=user_id)
        conv = (
            db.query(Conversation)
            .filter(Conversation.project_id == project_id, Conversation.user_id == user_id)
            .first()
        )
        if not conv:
            return []

        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )

        return [
            {
                "id": m.id,
                "conversation_id": m.conversation_id,
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata_json or {},
                "created_at": m.created_at
            }
            for m in messages
        ]


    @classmethod
    def clear_history(cls, db: Session, project_id: int, user_id: int) -> None:
        """
        Clear conversation history for a project.
        """
        ProjectService.get_project_by_id(db, project_id=project_id, user_id=user_id)
        conv = (
            db.query(Conversation)
            .filter(Conversation.project_id == project_id, Conversation.user_id == user_id)
            .first()
        )
        if conv:
            db.delete(conv)
            db.commit()
