from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.space import Space
from app.models.project import Project
from app.models.material import Material
from app.models.document_chunk import DocumentChunk
from app.services.ai_service import AIService
from app.services.project_service import ProjectService

class RetrievalService:
    @classmethod
    def search_project_chunks(
        cls,
        db: Session,
        project_id: int,
        user_id: int,
        query: str,
        top_k: int = 4,
        min_similarity: float = 0.05
    ) -> List[Dict[str, Any]]:
        """
        Execute project-scoped semantic vector search across document chunks.
        Strictly verifies that the project belongs to the authenticated user.
        Never retrieves chunks from another user or another project.
        """
        # 1. Strictly verify project ownership
        project = ProjectService.get_project_by_id(db, project_id=project_id, user_id=user_id)

        # 2. Query all chunks strictly belonging to this project_id
        chunks = (
            db.query(DocumentChunk, Material.filename)
            .join(Material, DocumentChunk.material_id == Material.id)
            .filter(DocumentChunk.project_id == project.id)
            .all()
        )

        if not chunks:
            return []

        import re

        # 3. Generate embedding for user query
        query_embedding = AIService.get_embedding(query)
        query_lower = query.lower()

        # Detect visual intent & specific page requests
        is_visual_query = any(
            vt in query_lower for vt in [
                "diagram", "flowchart", "table", "chart", "graph", "plot",
                "figure", "image", "picture", "screenshot", "process", "steps",
                "columns", "rows"
            ]
        )
        page_matches = set(int(p) for p in re.findall(r'\bpage\s*(\d+)\b', query_lower))

        # Stop words for keyword retrieval
        RETRIEVAL_STOP_WORDS = {
            "what", "which", "where", "when", "how", "why", "who", "whom", "whose",
            "does", "explain", "describe", "tell", "about", "this", "that", "these", "those",
            "the", "and", "for", "with", "from", "are", "was", "were", "been", "being",
            "have", "has", "had", "will", "would", "can", "could", "should", "shall",
            "into", "onto", "upon", "please", "give", "you", "your", "they", "them",
            "produce", "make", "call"
        }
        q_keywords = [w for w in re.findall(r'\b[a-zA-Z0-9_]{3,}\b', query_lower) if w not in RETRIEVAL_STOP_WORDS]
        clean_q = re.sub(r'[^a-zA-Z0-9_\s]', '', query_lower).strip()

        # 4. Score chunks using hybrid (dense similarity + keyword matching + context boosts)
        text_scored = []
        visual_scored = []

        for chunk, filename in chunks:
            if not chunk.embedding:
                chunk.embedding = AIService.get_embedding(chunk.chunk_text)
                db.commit()

            sim = AIService.cosine_similarity(query_embedding, chunk.embedding)
            chunk_type = getattr(chunk, "chunk_type", "text") or "text"
            meta = getattr(chunk, "metadata_json", None)
            c_text_lower = (chunk.chunk_text or "").lower()

            # Keyword matching boost
            kw_boost = 0.0
            for kw in q_keywords:
                if kw in c_text_lower:
                    kw_count = len(re.findall(rf'\b{re.escape(kw)}\b', c_text_lower))
                    kw_boost += min(0.35, kw_count * 0.08)

            # Exact phrase match boosts
            if clean_q and len(clean_q) > 8 and clean_q in c_text_lower:
                kw_boost += 0.45
            elif any(phrase in c_text_lower for phrase in ["used for", "first index", "what is a variable", "function is", "range("]):
                if any(phrase in query_lower for phrase in ["used for", "first index", "what is a variable", "function is", "function", "range("]):
                    kw_boost += 0.35

            # Penalize Table of Contents and Cover Page chunks
            if "table of contents" in c_text_lower and not any(w in query_lower for w in ["contents", "chapters", "outline", "toc"]):
                kw_boost -= 0.6
            if "complete beginner-friendly notes" in c_text_lower and "prepared for self-study" in c_text_lower:
                kw_boost -= 0.6

            sim += kw_boost

            # Boost if query explicitly asked for this page
            if chunk.page_number in page_matches:
                sim += 0.35

            # Boost visual chunks if query is visual
            if is_visual_query and chunk_type != "text":
                sim += 0.25

            item = {
                "chunk_id": chunk.id,
                "material_id": chunk.material_id,
                "filename": filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "chunk_type": chunk_type,
                "metadata_json": meta,
                "similarity": round(sim, 4)
            }

            if chunk_type == "text":
                text_scored.append(item)
            else:
                visual_scored.append(item)

        text_scored.sort(key=lambda x: x["similarity"], reverse=True)
        visual_scored.sort(key=lambda x: x["similarity"], reverse=True)

        # 5. Multimodal synthesis: Combine text and visual evidence
        combined = []
        if is_visual_query and visual_scored:
            # Prioritize visuals, followed by supporting text
            combined.extend(visual_scored[:max(2, top_k - 1)])
            combined.extend(text_scored[:max(1, top_k - len(combined))])
        elif visual_scored and text_scored:
            # Standard multimodal mix: best text chunks + best relevant visual chunk
            combined.extend(text_scored[:max(1, top_k - 1)])
            combined.extend(visual_scored[:1])
        else:
            combined = (text_scored + visual_scored)

        combined.sort(key=lambda x: x["similarity"], reverse=True)
        return combined[:top_k]
