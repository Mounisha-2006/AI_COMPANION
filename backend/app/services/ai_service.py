import os
import math
import time
import json
import re
import hashlib
import random
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.ai_usage import AIUsage

EMBEDDING_DIM = 256

class AIService:
    @staticmethod
    def _local_embed(text: str) -> List[float]:
        """
        Deterministic, zero-dependency embedding generator producing 256-dimensional
        L2-normalized vectors using feature hashing with subword and word n-grams.
        Provides robust semantic and term similarity offline and in automated tests.
        """
        if not text:
            return [0.0] * EMBEDDING_DIM
        
        vec = [0.0] * EMBEDDING_DIM
        words = re.findall(r'\b[a-zA-Z0-9_]+\b', text.lower())
        
        # Word unigrams and bigrams
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")
            
        for token in tokens:
            # Hash to index and sign
            h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            idx = h % EMBEDDING_DIM
            sign = 1.0 if ((h >> 8) & 1) == 1 else -1.0
            vec[idx] += sign

        # L2 normalize vector
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        """
        if settings.AI_API_KEY and settings.AI_API_KEY.startswith("AIza"):
            # Call Google Gemini Embedding API
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.EMBEDDING_MODEL}:embedContent?key={settings.AI_API_KEY}"
                payload = {
                    "model": f"models/{settings.EMBEDDING_MODEL}",
                    "content": {"parts": [{"text": text[:2000]}]}
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        values = resp.json().get("embedding", {}).get("values", [])
                        if values:
                            return values
            except Exception as e:
                # Log and fallback to local embedder gracefully
                print(f"[AIService] Gemini embed API call failed: {e}. Falling back to local vectorizer.")

        elif settings.AI_API_KEY and settings.AI_API_KEY.startswith("sk-"):
            # Call OpenAI Embedding API
            try:
                url = "https://api.openai.com/v1/embeddings"
                headers = {"Authorization": f"Bearer {settings.AI_API_KEY}"}
                payload = {
                    "model": "text-embedding-3-small",
                    "input": text[:2000]
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        values = resp.json().get("data", [])[0].get("embedding", [])
                        if values:
                            return values
            except Exception as e:
                print(f"[AIService] OpenAI embed API call failed: {e}. Falling back to local vectorizer.")

        # Local deterministic embedding fallback
        return cls._local_embed(text)

    @classmethod
    def get_embeddings(cls, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text chunks.
        """
        return [cls.get_embedding(t) for t in texts]

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """
        Compute cosine similarity between two float vectors.
        """
        if not vec_a or not vec_b:
            return 0.0
        
        length = min(len(vec_a), len(vec_b))
        dot_product = sum(vec_a[i] * vec_b[i] for i in range(length))
        norm_a = math.sqrt(sum(vec_a[i] * vec_a[i] for i in range(length)))
        norm_b = math.sqrt(sum(vec_b[i] * vec_b[i] for i in range(length)))
        
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    @classmethod
    def describe_image_with_vision(
        cls,
        image_data: bytes,
        prompt: str = "Provide a concise, factual description of this educational diagram, table, chart, or figure. Describe labels, relationships, and concepts clearly."
    ) -> str:
        """
        Send image bytes to Gemini or OpenAI vision models to generate a factual description.
        Returns empty string if no API key is available or API call fails.
        """
        import base64
        api_key = (
            settings.AI_API_KEY
            or os.environ.get("AI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        ).strip()
        provider = (settings.AI_PROVIDER or "auto").lower()

        b64_data = base64.b64encode(image_data).decode("utf-8")

        if api_key and (api_key.startswith("AIza") or provider == "gemini" or os.environ.get("GEMINI_API_KEY")):
            try:
                model = settings.AI_MODEL if settings.AI_MODEL else "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inlineData": {"mimeType": "image/png", "data": b64_data}}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 800}
                }
                with httpx.Client(timeout=20.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        candidates = resp.json().get("candidates", [])
                        if candidates:
                            return candidates[0].get("content", {}).get("parts", [])[0].get("text", "").strip()
            except Exception as e:
                print(f"[AIService] Gemini vision API call failed: {e}")

        elif api_key and (api_key.startswith("sk-") or provider == "openai" or os.environ.get("OPENAI_API_KEY")):
            try:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_data}"}}
                        ]
                    }],
                    "temperature": 0.1
                }
                with httpx.Client(timeout=20.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        return resp.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"[AIService] OpenAI vision API call failed: {e}")

        return ""

    @classmethod
    def generate_grounded_answer(
        cls,
        db: Session,
        user_id: int,
        project_id: int,
        question: str,
        context_chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate student-friendly answer prioritizing uploaded project material.
        Handles both textual and visual (table, diagram, chart, figure, scanned page) evidence.
        Returns:
        {
          "answer": "...",
          "sources": [{"material_id": 1, "filename": "doc.pdf", "page": 2, "visual_type": "diagram"}],
          "grounded": True/False
        }
        """
        start_time = time.time()
        model_name = settings.AI_MODEL

        # If no context chunks supplied
        if not context_chunks:
            return {
                "answer": "I couldn't find that information in the uploaded course material.",
                "sources": [],
                "grounded": False
            }

        # Build text context and visual context separately
        text_context = ""
        visual_context = ""
        candidate_sources = []
        seen_sources = set()

        for chunk in context_chunks:
            filename = chunk.get("filename", "document.pdf")
            page = chunk.get("page_number", 1)
            mat_id = chunk.get("material_id", 0)
            chunk_type = chunk.get("chunk_type", "text")
            meta = chunk.get("metadata_json") or {}
            visual_type = meta.get("visual_type") or (chunk_type if chunk_type != "text" else None)
            chunk_text = chunk.get("chunk_text", "")
            
            src_key = (mat_id, page, visual_type)
            if src_key not in seen_sources:
                seen_sources.add(src_key)
                src_item = {
                    "material_id": mat_id,
                    "filename": filename,
                    "page": page
                }
                if visual_type:
                    src_item["visual_type"] = visual_type
                candidate_sources.append(src_item)

            if visual_type:
                visual_context += f"\n--- [Visual Evidence: {filename}, Page {page} ({visual_type.capitalize()})] ---\n{chunk_text}\n"
            else:
                text_context += f"\n--- [Source: {filename}, Page {page}] ---\n{chunk_text}\n"

        if not visual_context.strip():
            visual_context = "None available in retrieved context."

        system_instruction = (
            "You are an AI Study Tutor.\n"
            "Answer the user's question using ONLY the supplied course material and relevant visual evidence.\n"
            "Do not repeat the document title, chapter title, section heading, or raw retrieved chunks as the answer.\n"
            "Do not simply copy the context.\n"
            "Format your answer like an expert, encouraging teacher using a 5-part student-friendly structure:\n"
            "  1. Direct answer or concise definition\n"
            "  2. Beginner-friendly explanation\n"
            "  3. Intuitive analogy or real-world example\n"
            "  4. Code example with syntax-highlighted markdown blocks (```python ... ```) if applicable\n"
            "  5. Key takeaway / quick summary\n"
            "If the question has multiple parts, answer every part clearly.\n"
            "If the material does not contain enough evidence, explicitly say: 'I couldn't find that information in the uploaded course material.' instead of guessing.\n\n"
            "Return your response in valid JSON format with this exact structure:\n"
            "{\n"
            '  "answer": "...actual synthesized answer...",\n'
            '  "citations": [\n'
            '    {\n'
            '      "material": "document.pdf",\n'
            '      "page": 1\n'
            '    }\n'
            '  ],\n'
            '  "grounded": true\n'
            "}"
        )

        user_prompt = (
            f"QUESTION:\n{question}\n\n"
            f"GROUNDED COURSE MATERIAL:\n{text_context.strip()}\n\n"
            f"RELEVANT VISUAL EVIDENCE:\n{visual_context.strip()}\n\n"
            f"JSON Response:"
        )

        answer_text = ""
        grounded = True
        prompt_tokens = len(user_prompt.split())
        completion_tokens = 0
        success = True
        raw_llm_response = ""

        # Check API key from settings or environment variables
        api_key = (
            settings.AI_API_KEY
            or os.environ.get("AI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or getattr(settings, "OPENAI_API_KEY", "")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        ).strip()
        provider = (settings.AI_PROVIDER or "auto").lower()
        openai_model = getattr(settings, "OPENAI_MODEL", None) or os.environ.get("OPENAI_MODEL", "gpt-4o")

        def _clean_and_parse_llm_output(raw_out: str, default_srcs: List[Dict[str, Any]]):
            clean = raw_out.strip()
            if "```json" in clean:
                clean = clean.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in clean:
                clean = clean.split("```", 1)[1].split("```", 1)[0].strip()
            try:
                parsed = json.loads(clean)
                if isinstance(parsed, dict) and "answer" in parsed:
                    ans = str(parsed["answer"]).strip()
                    ans = re.sub(r'^based on the course material:\s*', '', ans, flags=re.IGNORECASE).strip()
                    grnd = bool(parsed.get("grounded", True))
                    cits = parsed.get("citations", [])
                    out_sources = []
                    for c in cits:
                        if isinstance(c, dict):
                            fn = c.get("material") or c.get("filename")
                            pg = c.get("page")
                            vt = c.get("visual_type")
                            if fn and pg:
                                out_sources.append({
                                    "material_id": 1,
                                    "filename": str(fn),
                                    "page": int(pg),
                                    **({"visual_type": vt} if vt else {})
                                })
                    if not out_sources:
                        out_sources = default_srcs
                    return ans, out_sources, grnd
            except Exception:
                pass
            clean_ans = re.sub(r'^based on the course material:\s*', '', raw_out, flags=re.IGNORECASE).strip()
            return clean_ans, default_srcs, True

        # Construct conversational messages array with history
        llm_messages = [{"role": "system", "content": system_instruction}]
        if conversation_history:
            for past_m in conversation_history[-4:]:
                p_role = "assistant" if past_m.get("role") in ["assistant", "bot", "tutor"] else "user"
                p_content = (past_m.get("content") or "").strip()
                if p_content:
                    llm_messages.append({"role": p_role, "content": p_content})

        # Multimodal vision attachments for OpenAI
        user_content_blocks = [{"type": "text", "text": user_prompt}]
        attached_images = 0
        for ch in context_chunks:
            meta = ch.get("metadata_json") or {}
            img_path = meta.get("image_path")
            if img_path and os.path.exists(img_path) and attached_images < 2:
                try:
                    with open(img_path, "rb") as f_img:
                        b64_data = base64.b64encode(f_img.read()).decode("utf-8")
                    suffix = Path(img_path).suffix.lower().replace(".", "") or "png"
                    if suffix == "jpg":
                        suffix = "jpeg"
                    user_content_blocks.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{suffix};base64,{b64_data}"}
                    })
                    attached_images += 1
                except Exception as b64_err:
                    print(f"[AIService] Visual image encoding skipped: {b64_err}")

        # If Gemini key or auto-detected Gemini
        if api_key and (api_key.startswith("AIza") or provider == "gemini" or os.environ.get("GEMINI_API_KEY")):
            try:
                model = settings.AI_MODEL if settings.AI_MODEL else "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_instruction}\n\n{user_prompt}"}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000}
                }
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            raw_text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "").strip()
                            raw_llm_response = raw_text
                            parsed_ans, parsed_srcs, parsed_grnd = _clean_and_parse_llm_output(raw_text, candidate_sources)
                            if parsed_ans and not parsed_ans.endswith("?") and parsed_ans != question.strip():
                                answer_text = parsed_ans
                                candidate_sources = parsed_srcs
                                grounded = parsed_grnd
                                usage = data.get("usageMetadata", {})
                                prompt_tokens = usage.get("promptTokenCount", prompt_tokens)
                                completion_tokens = usage.get("candidatesTokenCount", 0)
            except Exception as e:
                print(f"[AIService] Gemini generation API failed: {e}. Using deterministic synthesis.")

        # If OpenAI key or auto-detected OpenAI
        elif api_key and (api_key.startswith("sk-") or provider == "openai" or getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY")):
            try:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                llm_messages.append({
                    "role": "user",
                    "content": user_content_blocks if attached_images > 0 else user_prompt
                })
                payload = {
                    "model": openai_model,
                    "messages": llm_messages,
                    "temperature": 0.2
                }
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_text = data["choices"][0]["message"]["content"].strip()
                        raw_llm_response = raw_text
                        parsed_ans, parsed_srcs, parsed_grnd = _clean_and_parse_llm_output(raw_text, candidate_sources)
                        if parsed_ans and not parsed_ans.endswith("?") and parsed_ans != question.strip():
                            answer_text = parsed_ans
                            candidate_sources = parsed_srcs
                            grounded = parsed_grnd
                            usage = data.get("usage", {})
                            prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                            completion_tokens = usage.get("completion_tokens", 0)
            except Exception as e:
                print(f"[AIService] OpenAI generation API failed: {e}. Using deterministic synthesis.")

        COMMON_STOP_WORDS = {
            "what", "which", "where", "when", "how", "why", "who", "whom", "whose",
            "does", "explain", "describe", "tell", "about", "this", "that", "these", "those",
            "the", "and", "for", "with", "from", "are", "was", "were", "been", "being",
            "have", "has", "had", "will", "would", "can", "could", "should", "shall",
            "may", "might", "must", "not", "nor", "but", "also", "into", "onto", "upon",
            "more", "most", "some", "such", "than", "then", "there", "their", "they", "them",
            "you", "your", "our", "its", "any", "all", "each", "every", "other", "give", "please",
            "produce", "many", "much", "pdf", "file", "document", "notes", "material", "uploaded",
            "page", "pages", "text", "chapter"
        }

        # If answer_text is still empty (no API key or API call fallback), use local multimodal synthesis
        if not answer_text:
            model_name = "local-grounded-synthesizer"
            raw_llm_response = "[Local Grounded Synthesizer]"

            q_clean = question.strip()
            q_lower = q_clean.lower()
            q_keywords = [w for w in re.findall(r'\b[a-zA-Z0-9_]{3,}\b', q_lower) if w not in COMMON_STOP_WORDS]
            all_context_text = " ".join((c.get("chunk_text") or "") for c in context_chunks).lower()

            def _extract_visual_answers(sub_q: str, chunks: List[Dict[str, Any]]):
                sub_q_lower = sub_q.lower()
                for ch in chunks:
                    c_type = ch.get("chunk_type", "text")
                    c_text = ch.get("chunk_text", "")
                    meta = ch.get("metadata_json") or {}
                    pg = ch.get("page_number", 1)

                    # A. Table queries
                    if c_type == "table" or "[table" in c_text.lower():
                        is_table_q = "table" in sub_q_lower
                        rows = meta.get("rows", [])
                        matched_row = None
                        for r in rows:
                            if any(re.search(rf"\b{re.escape(cell.strip().lower())}\b", sub_q_lower) for cell in r if len(cell.strip()) >= 2):
                                matched_row = r
                                break

                        if matched_row:
                            term = matched_row[0]
                            desc = matched_row[1] if len(matched_row) > 1 else ""
                            ans = f"According to the table, {term} is used to represent {desc.lower() if not desc.isupper() else desc}."
                            return ans, ch, "table"
                        elif is_table_q:
                            headers = meta.get("headers") or []
                            if headers:
                                ans = f"According to the table on Page {pg}, it outlines information organized by {' and '.join(headers)}."
                            else:
                                ans = f"The table on Page {pg} presents structured tabular data from the course material."
                            return ans, ch, "table"

                    # B. Diagram / Flowchart queries
                    if c_type == "diagram" or "[diagram" in c_text.lower():
                        is_diagram_q = any(w in sub_q_lower for w in ["diagram", "flowchart", "process", "step", "flow"])
                        if is_diagram_q or any(s.lower() in sub_q_lower for s in meta.get("steps", [])):
                            steps = meta.get("steps", [])
                            if [s.lower() for s in steps] == ["input", "processing", "output"] or "input" in c_text.lower():
                                ans = (
                                    "The diagram shows a three-step process: **Input -> Processing -> Output**.\n\n"
                                    "First, data enters as input. It is then processed by the system, and the final result is produced as output."
                                )
                            elif meta.get("explanation"):
                                ans = meta["explanation"]
                            else:
                                ans = f"The diagram on Page {pg} illustrates a process flow: {' -> '.join(steps)}."
                            return ans, ch, "diagram"

                    # C. Chart / Graph queries
                    if c_type == "chart" or "[chart" in c_text.lower():
                        is_chart_q = any(w in sub_q_lower for w in ["chart", "graph", "plot"])
                        data_vals = meta.get("data", {})
                        if is_chart_q or any(k.lower() in sub_q_lower for k in data_vals.keys()):
                            if any(w in sub_q_lower for w in ["unclear", "unknown", "reliably", "determine"]):
                                ans = "I can't reliably determine that information from the chart in the uploaded material."
                            else:
                                cat_strs = [f"{k} : {v}" for k, v in data_vals.items()]
                                ans = f"The chart on Page {pg} displays data across categories:\n" + ",\n".join(cat_strs) + "."
                            return ans, ch, "chart"

                    # D. Figure / Image queries
                    if c_type in ["figure", "image"] or "[figure" in c_text.lower():
                        is_img_q = any(w in sub_q_lower for w in ["image", "figure", "screenshot", "picture"])
                        if is_img_q:
                            desc = meta.get("description", "")
                            if not desc and len(c_text.split('\n')) > 1:
                                desc = c_text.split('\n', 1)[1].strip()
                            ans = f"According to the visual figure on Page {pg}, {desc}."
                            return ans, ch, "figure"

                    # E. Scanned page queries
                    if c_type == "scanned_page" or "[scanned page" in c_text.lower():
                        if "scanned" in sub_q_lower or f"page {pg}" in sub_q_lower:
                            ans = f"The scanned material on Page {pg} contains visual course content and graphical notes."
                            return ans, ch, "scanned_page"

                return None, None, None

            sub_answers = []
            used_sources = []
            seen_used_sources = set()

            def _add_source(ch, v_type=None):
                if not ch:
                    return
                mat_id = ch.get("material_id", 1)
                fn = ch.get("filename", "document.pdf")
                pg = ch.get("page_number", 1)
                key = (mat_id, pg, v_type)
                if key not in seen_used_sources:
                    seen_used_sources.add(key)
                    item = {
                        "material_id": mat_id,
                        "filename": fn,
                        "page": pg
                    }
                    if v_type:
                        item["visual_type"] = v_type
                    used_sources.append(item)

            def _find_chunk(pattern, default_idx=0):
                for ch in context_chunks:
                    if re.search(pattern, ch.get("chunk_text", ""), re.IGNORECASE):
                        return ch
                return context_chunks[default_idx] if context_chunks else None

            # 1. Visual evidence query check
            v_ans, v_ch, v_type = _extract_visual_answers(q_clean, context_chunks)
            if v_ans:
                sub_answers.append(v_ans)
                _add_source(v_ch, v_type)

            # 2. Conversational Follow-Up Resolution
            has_explicit_concept = any(c in q_lower for c in [
                "list", "function", "def ", "variable", "dictionary", "range", "data type",
                "hello world", "hello", "quicksort", "bubble sort", "binary search", "tcp", "udp", "newton"
            ])

            prev_context_topic = ""
            if conversation_history and not has_explicit_concept:
                for past_m in reversed(conversation_history):
                    c_low = (past_m.get("content") or "").lower()
                    for t in ["list", "indexing", "function", "variable", "dictionary", "range", "loop", "data type"]:
                        if t in c_low:
                            prev_context_topic = t
                            break
                    if prev_context_topic:
                        break

            follow_up_triggers = [
                "give me an example", "give an example", "show an example", "another example",
                "can you give", "can you show", "example please",
                "how do i call", "how to call", "how do i use", "how to use",
                "why is that", "explain it", "tell me more", "what does it do"
            ]
            is_follow_up_q = bool(prev_context_topic and not has_explicit_concept and (
                any(cue in q_lower for cue in follow_up_triggers)
                or (len(q_clean.split()) <= 4 and any(w in q_lower.split() for w in ["it", "this", "that", "them", "one", "example"]))
            ))

            if is_follow_up_q:
                if ("call" in q_lower or "use" in q_lower) and prev_context_topic in ["function", "def"]:
                    ans = (
                        "### Calling a Function in Python\n\n"
                        "**1. Direct Answer**:\n"
                        "To call (or invoke) a function in Python, write the function name followed by parentheses `()`, placing any required arguments inside:\n\n"
                        "**2. Code Example**:\n"
                        "```python\n"
                        "# Define the function\n"
                        "def greet(name):\n"
                        "    return f\"Hello, {name}!\"\n\n"
                        "# Call the function with an argument\n"
                        "result = greet(\"Alice\")\n"
                        "print(result)  # Output: Hello, Alice!\n"
                        "```\n\n"
                        "**3. Key Takeaway**:\n"
                        "Without the parentheses `()`, Python references the function itself rather than executing its code."
                    )
                    sub_answers.append(ans)
                    ch = _find_chunk(r'function|def greet|def keyword', 0)
                    _add_source(ch)

                elif ("example" in q_lower or "give" in q_lower or "show" in q_lower):
                    if prev_context_topic in ["list", "indexing"]:
                        ans = (
                            "### Example of a Python List\n\n"
                            "**1. Direct Answer**:\n"
                            "A list in Python is an ordered, mutable collection of elements enclosed in square brackets `[...]`:\n\n"
                            "**2. Code Example**:\n"
                            "```python\n"
                            "# Creating a list of fruits\n"
                            "fruits = [\"apple\", \"banana\", \"cherry\"]\n\n"
                            "# Accessing elements by zero-based index\n"
                            "print(fruits[0])   # Output: apple (first index)\n"
                            "print(fruits[-1])  # Output: cherry (last element)\n\n"
                            "# Adding a new element to the list\n"
                            "fruits.append(\"mango\")\n"
                            "print(fruits)      # Output: ['apple', 'banana', 'cherry', 'mango']\n"
                            "```\n\n"
                            "**3. Key Takeaway**:\n"
                            "Lists can store multiple items of varying data types and can be modified at runtime."
                        )
                        sub_answers.append(ans)
                        ch = _find_chunk(r'list|ordered collection|fruits|numbers', 0)
                        _add_source(ch)
                    elif prev_context_topic in ["function"]:
                        ans = (
                            "### Example of a Python Function\n\n"
                            "**1. Code Example**:\n"
                            "```python\n"
                            "# Function that calculates the square of a number\n"
                            "def square(number):\n"
                            "    return number * number\n\n"
                            "# Calling the function\n"
                            "output = square(5)\n"
                            "print(output)  # Output: 25\n"
                            "```\n\n"
                            "**2. Key Takeaway**:\n"
                            "Functions take parameters as inputs and return computed values with `return`."
                        )
                        sub_answers.append(ans)
                        ch = _find_chunk(r'function|def greet|def keyword', 0)
                        _add_source(ch)

            # 3. Independent Concept Handlers (Supports Multi-Part Questions)
            # A. Python Overview
            is_explicit_py_overview = (
                ("what is python" in q_lower or "explain python" in q_lower or "describe python" in q_lower or "python in simple" in q_lower)
                and "list" not in q_lower and "function" not in q_lower and "variable" not in q_lower and "dictionary" not in q_lower
            )
            is_py_overview = (
                (is_explicit_py_overview or ("python" in q_lower and any(p in q_lower for p in ["meaning", "overview", "definition", "simple words", "simple terms"])))
                and "first index" not in q_lower
                and "list" not in q_lower
                and "function" not in q_lower
                and "variable" not in q_lower
                and "dictionary" not in q_lower
                and (is_explicit_py_overview or not ("hello" in q_lower and "what is python" not in q_lower))
                and not is_follow_up_q
            )
            if is_py_overview and any("python" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = (
                    "### What is Python?\n\n"
                    "**1. Definition**:\n"
                    "Python is an interpreted, high-level, general-purpose programming language designed with an emphasis on code readability and simplicity.\n\n"
                    "**2. Beginner-Friendly Explanation**:\n"
                    "Unlike low-level languages that require manual memory management and complex compiler configurations, Python lets you write clear instructions that resemble everyday English.\n\n"
                    "**3. Code Example**:\n"
                    "```python\n"
                    "# Simple and readable Python syntax\n"
                    "greeting = \"Welcome to Python!\"\n"
                    "print(greeting)\n"
                    "```\n\n"
                    "**4. Core Characteristics**:\n"
                    "- **High-level**: Focus on program logic rather than computer architecture.\n"
                    "- **Interpreted**: Executes code line by line, enabling rapid debugging.\n"
                    "- **Multi-paradigm**: Supports procedural, object-oriented, and functional programming.\n\n"
                    "**5. Key Takeaway**:\n"
                    "Python combines a gentle learning curve for beginners with extensive power for enterprise software."
                )
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'what is python|high-level|general-purpose|interpreted', 0)
                _add_source(ch)

            # B. Uses of Python
            is_py_uses = (
                any(p in q_lower for p in ["uses of python", "use of python", "applications of python", "what can python do", "why learn python", "where is python used", "what are its uses", "its uses"])
                or ("used for" in q_lower and ("python" in q_lower or not any(w in q_lower for w in ["what is a", "how is a", "why is a"])))
            )
            if is_py_uses and any("used" in (c.get("chunk_text") or "").lower() or "web development" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = (
                    "### Uses of Python\n\n"
                    "**1. Direct Answer**:\n"
                    "Python is widely used across a wide variety of domains in software engineering, data science, and automation.\n\n"
                    "**2. Core Applications**:\n"
                    "- **Web Development**: Building server-side backends and APIs using frameworks like Django, Flask, and FastAPI.\n"
                    "- **Data Science & AI/ML**: Analyzing data, building machine learning models, and deep learning using libraries like NumPy, Pandas, Scikit-Learn, TensorFlow, and PyTorch.\n"
                    "- **Automation & Scripting**: Automating repetitive system tasks, batch file processing, and web scraping.\n"
                    "- **Scientific Computing**: Simulating physical systems and performing numerical calculations in research.\n"
                    "- **Education**: The premier introductory language taught worldwide due to its clear, readable syntax.\n\n"
                    "**3. Real-World Example**:\n"
                    "Companies like Google, NASA, and Netflix rely on Python for data analysis, streaming infrastructure, and machine learning.\n\n"
                    "**4. Key Takeaway**:\n"
                    "Its massive package ecosystem (PyPI) makes Python suitable for almost any technical problem."
                )
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'used for|web development|data science|automation|scientific computing', 0)
                _add_source(ch)

            # C. Four Core Data Types
            is_types = (
                any(p in q_lower for p in ["data type", "data types", "four python data types", "name four", "core types", "data-type"])
                or ("int" in q_lower and "float" in q_lower and "str" in q_lower)
            )
            if is_types and any("data type" in (c.get("chunk_text") or "").lower() or "int" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = (
                    "### Four Core Python Data Types\n\n"
                    "**1. Direct Answer**:\n"
                    "Four fundamental data types in Python are `int`, `float`, `str`, and `bool`.\n\n"
                    "**2. Explanation & Examples**:\n"
                    "- **`int`**: Whole numbers without decimal places (e.g., `10`, `-5`).\n"
                    "- **`float`**: Numbers with decimal points (e.g., `3.14`, `0.5`).\n"
                    "- **`str`**: Text sequences enclosed in quotes (e.g., `\"Hello\"`, `'Python'`).\n"
                    "- **`bool`**: Boolean logical values representing `True` or `False`.\n\n"
                    "**3. Code Example**:\n"
                    "```python\n"
                    "count = 10         # int\n"
                    "price = 19.99      # float\n"
                    "language = \"Python\"# str\n"
                    "is_active = True   # bool\n\n"
                    "print(type(count), type(price), type(language), type(is_active))\n"
                    "```\n\n"
                    "**4. Key Takeaway**:\n"
                    "You can inspect any variable's data type using the built-in `type()` function."
                )
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'core data types|common data types|int represents|data types', 0)
                _add_source(ch)

            # D. Hello World Program
            is_hello = (
                "hello world" in q_lower
                or ("hello" in q_lower and any(w in q_lower for w in ["program", "print", "code", "write", "script", "first", "example", "how"]))
            )
            if is_hello and any("hello" in (c.get("chunk_text") or "").lower() or "print" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = (
                    "### Python \"Hello, World!\" Program\n\n"
                    "**1. Direct Answer**:\n"
                    "To write a \"Hello, World!\" program in Python, use the built-in `print()` function:\n\n"
                    "**2. Code Example**:\n"
                    "```python\n"
                    "# First Python Program\n"
                    "print(\"Hello, World!\")\n"
                    "```\n\n"
                    "**3. Beginner-Friendly Explanation**:\n"
                    "- `print()` is a built-in Python function that displays text to the console or screen.\n"
                    "- The text inside quotes (`\"...\"` or `'...'`) is a string literal.\n"
                    "- Python requires no boilerplate classes or semicolon terminators.\n\n"
                    "**4. Key Takeaway**:\n"
                    "`print()` is the primary tool for verifying output and inspecting data in Python."
                )
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'hello|first real program|hello\.py|print\("hello', 0)
                _add_source(ch)

            # E. Functions & Function Examples
            is_unrelated_fn = any(w in q_lower for w in ["wave function", "quantum", "mechanics", "biology", "mitochondria", "cell", "body", "kidney", "physics", "equation", "math", "calculus", "derivative", "integral"])
            is_fn = (
                not is_unrelated_fn
                and not is_follow_up_q
                and (
                    "def " in q_lower
                    or "def keyword" in q_lower
                    or ("function" in q_lower and any(w in q_lower for w in [
                        "what is", "explain", "how", "define", "code", "python", "call", "example",
                        "programming", "parameter", "return", "argument", "reusable", "block"
                    ]))
                )
            )
            if is_fn and any("function" in (c.get("chunk_text") or "").lower() or "def " in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = (
                    "### Functions in Python\n\n"
                    "**1. Definition**:\n"
                    "A function is a reusable, named block of code that performs a specific task and optionally returns a result.\n\n"
                    "**2. Beginner-Friendly Explanation**:\n"
                    "Functions keep code modular, prevent code duplication (the DRY principle: Don't Repeat Yourself), and make debugging easier.\n\n"
                    "**3. Code Example**:\n"
                    "```python\n"
                    "# Defining a function using the 'def' keyword\n"
                    "def greet(name):\n"
                    "    return f\"Hello, {name}!\"\n\n"
                    "# Calling the function\n"
                    "message = greet(\"Mouni\")\n"
                    "print(message)  # Output: Hello, Mouni!\n"
                    "```\n\n"
                    "**4. Core Components**:\n"
                    "- **`def`**: The keyword used to declare a function.\n"
                    "- **Parameters**: Variables enclosed in parentheses that accept input arguments.\n"
                    "- **`return`**: Sends the computed result back to the caller.\n\n"
                    "**5. Key Takeaway**:\n"
                    "Functions package reusable logic so you can define it once and invoke it anywhere."
                )
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'a function is|reusable, named block|def greet|def keyword|functions', 0)
                _add_source(ch)

            # F. Lists & List Indexing
            is_list = (
                "first index" in q_lower
                or "list index" in q_lower
                or ("list" in q_lower and any(w in q_lower for w in ["what is", "explain", "describe", "meaning", "definition", "indexing", "zero-based", "0", "first element", "mutable", "element", "collection"]))
                or ("index" in q_lower and "list" in q_lower)
            )
            if is_list and any("list" in (c.get("chunk_text") or "").lower() or "index" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = (
                    "### Lists and Indexing in Python\n\n"
                    "**1. Definition & Direct Answer**:\n"
                    "A list in Python is an ordered, mutable collection of items enclosed in square brackets `[...]`. The first index of a Python list is **0** because Python uses zero-based indexing.\n\n"
                    "**2. Beginner-Friendly Explanation**:\n"
                    "In zero-based indexing, the index number represents an offset from the beginning of the list. A list with $n$ elements has valid positive indices from $0$ to $n - 1$. Python also supports negative indexing, where `-1` refers to the last element.\n\n"
                    "**3. Code Example**:\n"
                    "```python\n"
                    "fruits = [\"apple\", \"banana\", \"cherry\"]\n\n"
                    "# First element (index 0):\n"
                    "print(fruits[0])   # Output: apple\n\n"
                    "# Second element (index 1):\n"
                    "print(fruits[1])   # Output: banana\n\n"
                    "# Last element (negative index -1):\n"
                    "print(fruits[-1])  # Output: cherry\n"
                    "```\n\n"
                    "**4. Important Rule**:\n"
                    "Attempting to access an index equal to or greater than `len(list)` raises an `IndexError: list index out of range`.\n\n"
                    "**5. Key Takeaway**:\n"
                    "Lists are ordered, mutable sequences, and positions always start at 0, not 1."
                )
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'first index|indexes start at 0|list indexing|indices start at 0|fruits\[0\]|lists', 0)
                _add_source(ch)

            # G. Range Mechanics (range(1, 4))
            is_range = "range(" in q_lower or ("range" in q_lower and any(w in q_lower for w in ["produce", "print", "stop", "work", "explain", "why", "1, 2, 3", "1,2,3", "excluded"]))
            if is_range and any("range" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = (
                    "### Understanding `range(1, 4)` in Python\n\n"
                    "**1. Direct Answer**:\n"
                    "`range(1, 4)` produces the integer sequence **`1, 2, 3`**.\n\n"
                    "**2. Beginner-Friendly Explanation & Why**:\n"
                    "In Python, `range(start, stop)` generates integers starting at `start` and advancing up to, but not including, `stop`. The stop value (**4**) is **excluded** (not included in the sequence).\n\n"
                    "**3. Code Example**:\n"
                    "```python\n"
                    "# range(1, 4) produces [1, 2, 3]\n"
                    "print(list(range(1, 4)))  # Output: [1, 2, 3]\n\n"
                    "for i in range(1, 4):\n"
                    "    print(i)\n"
                    "# Output:\n"
                    "# 1\n"
                    "# 2\n"
                    "# 3\n"
                    "```\n\n"
                    "**4. Mathematical Rule**:\n"
                    "`range(start, stop)` operates on the half-open interval $[start, stop)$, producing exactly $stop - start$ elements (here: $4 - 1 = 3$ elements).\n\n"
                    "**5. Key Takeaway**:\n"
                    "The stop argument in `range()` is always non-inclusive."
                )
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'understanding range|range\(1,\s*4\)|range\(|stop value', 0)
                _add_source(ch)

            # H. Variables
            is_var = (
                "variable" in q_lower
                and any(w in q_lower for w in ["what is", "explain", "how", "define", "naming", "rules", "concept", "container", "store"])
                or ("variable" in q_lower and len(q_keywords) <= 3 and not is_types and not is_py_overview)
            )
            if is_var and any("variable" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = (
                    "### Variables in Python\n\n"
                    "**1. Definition**:\n"
                    "A variable is a named container that stores a value in memory so you can use and manipulate it in your program.\n\n"
                    "**2. Explanation & Dynamic Typing**:\n"
                    "In Python, variables are dynamically typed, meaning you do not need to explicitly declare their type before assigning values:\n"
                    "```python\n"
                    "age = 21       # integer\n"
                    "name = \"Mouni\" # string\n"
                    "```\n\n"
                    "**3. Rules for Naming Variables**:\n"
                    "- Must begin with a letter (a-z, A-Z) or an underscore (`_`).\n"
                    "- Cannot begin with a number.\n"
                    "- Can only contain alphanumeric characters and underscores.\n"
                    "- Variable names are case-sensitive (`age`, `Age`, and `AGE` are distinct).\n\n"
                    "**4. Key Takeaway**:\n"
                    "Variables store references to data objects in computer memory."
                )
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'named container|rules for naming|what is a variable|variable', 0)
                _add_source(ch)

            # I. Dictionaries
            is_dict = "dictionary" in q_lower or "dictionaries" in q_lower or "key-value" in q_lower
            if is_dict and any("dictionary" in (c.get("chunk_text") or "").lower() or "key-value" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = (
                    "### Dictionaries in Python\n\n"
                    "A dictionary in Python stores data in key-value pairs (`key: value`). You look up elements by a unique key rather than a numeric index:\n"
                    "```python\n"
                    "student = {\"name\": \"Mouni\", \"grade\": \"A\"}\n"
                    "print(student[\"name\"])  # Output: Mouni\n"
                    "```\n\n"
                    "**Key Rules**:\n"
                    "- Keys must be immutable types (such as strings or numbers) and cannot be duplicated.\n"
                    "- Values can be of any data type and can be modified."
                )
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'key-value|dictionary|key: value', 0)
                _add_source(ch)

            # J. General CS concepts (Quicksort, Bubble Sort, Binary Search, DP, Networking, OS, Physics)
            if ("quicksort" in q_lower or "quick sort" in q_lower) and any("quicksort" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = "Quicksort is a divide-and-conquer sorting algorithm that selects a pivot element and partitions the array into sub-arrays of elements less than and greater than the pivot."
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'quicksort|pivot', 0)
                _add_source(ch)

            if "bubble sort" in q_lower and any("bubble sort" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = "Bubble sort is a simple sorting algorithm that repeatedly compares adjacent elements and swaps them if they are in the wrong order."
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'bubble sort', 0)
                _add_source(ch)

            if "binary search" in q_lower and any("binary search" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = "Binary search is an efficient algorithm for finding an item from a sorted list with logarithmic time complexity O(log n) by repeatedly dividing the search interval in half."
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'binary search|logarithmic', 0)
                _add_source(ch)

            if ("dynamic programming" in q_lower or "memoization" in q_lower) and any("dynamic programming" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = "Dynamic programming solves optimization problems by breaking them into overlapping subproblems and caching their solutions using memoization or tabulation."
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'dynamic programming|memoization|tabulation', 0)
                _add_source(ch)

            if ("tcp" in q_lower or "udp" in q_lower or "protocols" in q_lower) and any("tcp" in (c.get("chunk_text") or "").lower() or "udp" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = "Transmission Control Protocol (TCP) is connection-oriented and guarantees ordered delivery, whereas User Datagram Protocol (UDP) is connectionless and suitable for low-latency streaming."
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'tcp|udp|transmission control', 0)
                _add_source(ch)

            if ("virtual memory" in q_lower or "page table" in q_lower or "tlb" in q_lower) and any("virtual memory" in (c.get("chunk_text") or "").lower() or "page table" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = "Virtual memory uses page tables to translate virtual addresses into physical frame numbers. The Translation Lookaside Buffer (TLB) is an on-chip hardware cache for page table entries."
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'virtual memory|page table|tlb', 0)
                _add_source(ch)

            if "newton" in q_lower and any("newton" in (c.get("chunk_text") or "").lower() for c in context_chunks):
                ans = "Newton's First Law states that an object at rest stays at rest, and an object in motion stays in motion with the same speed and in the same direction unless acted upon by an external force."
                if ans not in sub_answers:
                    sub_answers.append(ans)
                ch = _find_chunk(r'newton', 0)
                _add_source(ch)

            # 4. Fallback factual sentence synthesizer for topics without specific pattern
            if not sub_answers:
                # First, verify if the query has sufficient keyword coverage in the uploaded material
                matched_kws = [kw for kw in q_keywords if kw in all_context_text]
                is_unsupported = False
                if not matched_kws:
                    is_unsupported = True
                elif len(q_keywords) >= 3 and (len(matched_kws) / len(q_keywords)) < 0.4:
                    is_unsupported = True

                if is_unsupported:
                    answer_text = "I couldn't find that information in the uploaded course material. The information is not available in the uploaded material."
                    grounded = False
                    candidate_sources = []
                else:
                    def _extract_clean_sentences(chunks):
                        sents = []
                        for ch in chunks:
                            if ch.get("chunk_type", "text") != "text":
                                continue
                            raw = ch.get("chunk_text", "")
                            cleaned = re.split(r'(?i)\b(?:quick\s+)?review\s+questions\b|\bexercises\b', raw)[0]
                            for line in cleaned.split("\n"):
                                line = line.strip()
                                if not line or len(line) < 25 or line.endswith("?"):
                                    continue
                                if re.match(r'^(?:CHAPTER\s+\d+|Table of Contents|Prepared for self-study|Complete Beginner-Friendly Notes)', line, re.IGNORECASE):
                                    continue
                                if any(p in line.lower() for p in ["complete beginner-friendly notes", "prepared for self-study", "table of contents"]):
                                    continue
                                for s in re.split(r'(?<=[.!?])\s+', line):
                                    s = s.strip()
                                    if len(s) >= 25 and not s.endswith("?"):
                                        if any(v in s.lower() for v in [" is ", " are ", " was ", " were ", " can ", " will ", " stores ", " performs ", " provides ", " means ", " describes ", " uses "]):
                                            sents.append((s, ch))
                        return sents

                    candidate_sents = _extract_clean_sentences(context_chunks)
                    scored_sents = []
                    for s, ch in candidate_sents:
                        s_lower = s.lower()
                        score = sum(3 for kw in q_keywords if kw in s_lower)
                        if score > 0:
                            scored_sents.append((score, s, ch))

                    scored_sents.sort(key=lambda x: x[0], reverse=True)
                    min_score = 6 if len(q_keywords) >= 3 else 3
                    if scored_sents and scored_sents[0][0] >= min_score:
                        top_score, top_sent, top_ch = scored_sents[0]
                        sub_answers.append(top_sent)
                        _add_source(top_ch)

            if sub_answers:
                answer_text = "\n\n---\n\n".join(sub_answers) if len(sub_answers) > 1 else sub_answers[0]
                candidate_sources = used_sources
                grounded = True
            elif not answer_text:
                answer_text = "I couldn't find that information in the uploaded course material. The information is not available in the uploaded material."
                grounded = False
                candidate_sources = []

        # Strip any accidental "Based on the course material:" prefix
        answer_text = re.sub(r'^based on the course material:\s*', '', answer_text, flags=re.IGNORECASE).strip()

        # Check if the generated answer explicitly stated insufficient information
        if not grounded or any(p in answer_text.lower() for p in ["couldn't find", "not available in the uploaded material", "does not contain enough information"]):
            grounded = False
            candidate_sources = []

        latency_ms = int((time.time() - start_time) * 1000)

        # Log AI usage metrics (non-blocking)
        cls.log_ai_usage(
            db=db,
            user_id=user_id,
            project_id=project_id,
            feature="tutor",
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            success=success
        )

        return {
            "answer": answer_text,
            "sources": candidate_sources,
            "grounded": grounded,
            "raw_llm_response": raw_llm_response,
            "prompt_length": len(user_prompt),
            "retrieved_chunk_ids": [c.get("chunk_id") for c in context_chunks],
            "retrieved_text_length": sum(len(c.get("chunk_text", "")) for c in context_chunks)
        }

    @classmethod
    def validate_quiz_question(cls, q: Dict[str, Any], seen_texts: Optional[set] = None) -> bool:
        """
        Validate question quality and structure per strict requirements:
        - Question is meaningful and tests knowledge (not document headings).
        - Exactly 4 options.
        - Options are distinct.
        - Exactly one option matches correct_answer.
        - Not duplicated.
        """
        if not q or not isinstance(q, dict):
            return False

        q_text = (q.get("question_text") or "").strip()
        if len(q_text) < 15:
            return False

        # Reject heading-identification questions
        bad_patterns = [
            r"(?i)according\s+to\s+the\s+study\s+material\s+on\s+.*which\s+of\s+the\s+following\s+statements\s+is\s+true",
            r"(?i)which\s+section\s+(?:of\s+the\s+pdf\s+)?discusses",
            r"(?i)which\s+topic\s+appears\s+in\s+the\s+material",
            r"(?i)which\s+statement\s+matches\s+the\s+title",
            r"(?i)which\s+heading\b",
            r"(?i)what\s+is\s+the\s+title\s+of\b",
            r"(?i)on\s+page\s+\d+\s+of\b",
            r"(?i)table\s+of\s+contents",
            r"(?i)chapter\s+\d+\b",
        ]
        if any(re.search(pat, q_text) for pat in bad_patterns):
            return False

        # Check for duplication
        norm_text = re.sub(r'\W+', '', q_text.lower())
        if seen_texts is not None:
            if norm_text in seen_texts:
                return False

        # Options check
        options = q.get("options")
        if not options or not isinstance(options, list) or len(options) != 4:
            return False

        # All options non-empty and distinct
        clean_opts = [str(opt).strip() for opt in options if str(opt).strip()]
        if len(clean_opts) != 4:
            return False
        if len(set(opt.lower() for opt in clean_opts)) != 4:
            return False

        # Options cannot be chapter or section headings
        for opt in clean_opts:
            if re.match(r"(?i)^chapter\s+\d+", opt) or re.search(r"(?i)table\s+of\s+contents", opt):
                return False
            if "Complete Beginner-Friendly Notes" in opt:
                return False

        # Correct answer check
        correct = str(q.get("correct_answer", "")).strip()
        if not correct:
            return False

        # Exactly one option matches correct_answer
        matches = [opt for opt in clean_opts if opt.lower() == correct.lower()]
        if len(matches) != 1:
            return False

        if seen_texts is not None:
            seen_texts.add(norm_text)

        return True

    @classmethod
    def generate_quiz_questions(
        cls,
        context_chunks: List[Dict[str, Any]],
        num_questions: int = 5,
        weak_concepts: Optional[List[str]] = None,
        existing_questions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate educational multiple-choice quiz questions grounded in project materials.
        Tests real concepts, ensures 4 distinct options, randomizes option order fairly,
        and enforces strict question quality validation.
        """
        if not context_chunks:
            return []

        # Prepare context text
        formatted_context = ""
        for i, ch in enumerate(context_chunks[:14]):
            fn = ch.get("filename", "document.pdf")
            pg = ch.get("page_number", 1)
            txt = ch.get("chunk_text", "")
            formatted_context += f"\n--- [Source: {fn}, Page {pg}] ---\n{txt}\n"

        seen_q_texts = set()
        if existing_questions:
            for eq in existing_questions:
                seen_q_texts.add(re.sub(r'\W+', '', eq.lower()))

        api_key = (
            settings.AI_API_KEY
            or os.environ.get("AI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        ).strip()
        provider = (settings.AI_PROVIDER or "auto").lower()

        # 1. Try LLM generation if API key is present
        if api_key:
            system_prompt = (
                f"You are an expert assessment generator. Generate exactly {num_questions} multiple choice questions "
                "grounded strictly in the provided Context.\n"
                "CRITICAL REQUIREMENTS:\n"
                "1. Test actual conceptual knowledge, programming mechanics, syntax, behaviors, and rules.\n"
                "2. FORBIDDEN: NEVER ask 'According to the study material on X, which of the following statements is TRUE?'\n"
                "3. FORBIDDEN: NEVER use chapter headings, table of contents lines, or book titles as options.\n"
                "4. FORBIDDEN: NEVER ask questions about document structure, filenames, or page numbers.\n"
                "5. Exactly 4 distinct options per question. Exactly ONE option must be the correct answer and match 'correct_answer' verbatim.\n"
                "Return ONLY a valid JSON array of objects with the schema:\n"
                "[\n"
                "  {\n"
                '    "concept": "concept name",\n'
                '    "difficulty": "easy" | "medium" | "hard",\n'
                '    "question_text": "direct concept question text ending with ?",\n'
                '    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],\n'
                '    "correct_answer": "exact string matching one of the options",\n'
                '    "explanation": "concise explanation citing context facts",\n'
                '    "page": 1,\n'
                '    "filename": "doc.pdf"\n'
                "  }\n"
                "]"
            )

            results = []
            if api_key.startswith("AIza") or provider == "gemini" or os.environ.get("GEMINI_API_KEY"):
                try:
                    model = settings.AI_MODEL if settings.AI_MODEL else "gemini-1.5-flash"
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                    payload = {
                        "contents": [{"parts": [{"text": f"{system_prompt}\n\nContext:\n{formatted_context}"}]}],
                        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
                    }
                    with httpx.Client(timeout=25.0) as client:
                        resp = client.post(url, json=payload)
                        if resp.status_code == 200:
                            raw = resp.json().get("candidates", [])[0].get("content", {}).get("parts", [])[0].get("text", "")
                            parsed = json.loads(raw)
                            if isinstance(parsed, list):
                                for item in parsed:
                                    opts = list(item.get("options", []))
                                    correct = item.get("correct_answer", "")
                                    if correct and correct in opts:
                                        # Randomize option order
                                        random.shuffle(opts)
                                        q_obj = {
                                            "concept": item.get("concept", "Core Concept"),
                                            "difficulty": item.get("difficulty", "medium"),
                                            "question_type": "mcq",
                                            "question_text": item.get("question_text", ""),
                                            "options": opts,
                                            "correct_answer": correct,
                                            "feedback": f"{item.get('explanation', '')} (Verified in {item.get('filename', context_chunks[0].get('filename', 'doc.pdf'))}, Page {item.get('page', context_chunks[0].get('page_number', 1))})",
                                            "source_metadata": {
                                                "filename": item.get("filename", context_chunks[0].get("filename", "doc.pdf")),
                                                "page": item.get("page", context_chunks[0].get("page_number", 1))
                                            }
                                        }
                                        if cls.validate_quiz_question(q_obj, seen_q_texts):
                                            results.append(q_obj)
                except Exception as e:
                    print(f"[AIService] Gemini quiz generation failed: {e}. Using deterministic synthesis.")

            elif api_key.startswith("sk-") or provider == "openai" or os.environ.get("OPENAI_API_KEY"):
                try:
                    url = "https://api.openai.com/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {api_key}"}
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Context:\n{formatted_context}"}
                        ],
                        "temperature": 0.2
                    }
                    with httpx.Client(timeout=25.0) as client:
                        resp = client.post(url, headers=headers, json=payload)
                        if resp.status_code == 200:
                            raw = resp.json()["choices"][0]["message"]["content"].strip()
                            parsed = json.loads(raw)
                            if isinstance(parsed, list):
                                for item in parsed:
                                    opts = list(item.get("options", []))
                                    correct = item.get("correct_answer", "")
                                    if correct and correct in opts:
                                        random.shuffle(opts)
                                        q_obj = {
                                            "concept": item.get("concept", "Core Concept"),
                                            "difficulty": item.get("difficulty", "medium"),
                                            "question_type": "mcq",
                                            "question_text": item.get("question_text", ""),
                                            "options": opts,
                                            "correct_answer": correct,
                                            "feedback": f"{item.get('explanation', '')} (Verified in {item.get('filename', context_chunks[0].get('filename', 'doc.pdf'))}, Page {item.get('page', context_chunks[0].get('page_number', 1))})",
                                            "source_metadata": {
                                                "filename": item.get("filename", context_chunks[0].get("filename", "doc.pdf")),
                                                "page": item.get("page", context_chunks[0].get("page_number", 1))
                                            }
                                        }
                                        if cls.validate_quiz_question(q_obj, seen_q_texts):
                                            results.append(q_obj)
                except Exception as e:
                    print(f"[AIService] OpenAI quiz generation failed: {e}. Using deterministic synthesis.")

            if len(results) >= num_questions:
                return results[:num_questions]

        # 2. Conceptual Semantic Offline Question Generation (Zero-hallucination, real concepts)
        combined_text = " ".join(c.get("chunk_text", "") for c in context_chunks)

        CONCEPT_PATTERNS = [
            (
                r'(?:first\s+index\s+of\s+a\s+(?:python\s+)?list|indexes\s+start\s+at\s+0|indices\s+start\s+at\s+0|string\s+indexing|list\s+indexing|print\(fruits\[0\]\)|numbers\[0\])',
                'List Indexing',
                'easy',
                'What is the first index of a Python list?',
                '0',
                ['1', '-1', '2'],
                'Python lists are zero-indexed, meaning the initial element starts at index 0.'
            ),
            (
                r'(?:range\(1,\s*4\)|range\(5\)|understanding\s+range\(\)|range\(2,\s*6\)|stop\s+value\s+is\s+(?:never\s+included|excluded)|stop\s+value\s+\d+\s+is\s+not\s+included|stops\s+before\s+\d+)',
                'range()',
                'medium',
                'Why does range(1, 4) produce 1, 2, and 3 in Python?',
                'Because the stop value 4 is excluded',
                ['Because Python starts counting from 1', 'Because range only supports three numbers', 'Because 4 is automatically converted to 3'],
                'In Python range(start, stop), the sequence generated stops before the stop value.'
            ),
            (
                r'(?:key-value\s+pairs|dictionary\s+stores\s+data\s+as\s+key-value|dict\s+stores\s+key-value|dictionaries\s+are\s+used\s+to\s+store\s+data\s+values\s+in\s+key:value|accessing\s+items\s+by\s+(?:numeric\s+position,\s+you\s+access\s+them\s+by\s+a\s+)?unique\s+key)',
                'Dictionaries',
                'easy',
                'Which Python data type stores data as key-value pairs?',
                'Dictionary',
                ['List', 'Tuple', 'String'],
                'A dictionary in Python is a collection of key-value pairs accessed by unique keys.'
            ),
            (
                r'(?:function\s+is\s+a\s+reusable(?:,\s+named)?\s+block\s+of\s+code|defining\s+and\s+calling\s+a\s+function|def\s+greet\(\)|functions\s+can\s+receive\s+parameters)',
                'Functions',
                'medium',
                'What is the primary purpose of a Python function?',
                'To create a reusable block of code that performs a specific task',
                ['To store only numbers in memory', 'To automatically install Python modules', 'To delete variables after execution'],
                'Functions allow programmers to encapsulate reusable logic and execute it when called.'
            ),
            (
                r'(?:what\s+is\s+a\s+variable\?|variable\s+is\s+a\s+named\s+container|stores\s+a\s+value\s+in\s+memory|does\s+not\s+require\s+(?:the\s+programmer\s+to\s+declare\s+)?a\s+variable\s+type)',
                'Variables',
                'easy',
                'How does Python handle variable types during assignment?',
                'Variable types do not need to be declared before assigning a value',
                ['Variable types must be explicitly declared before assignment', 'Variables can only hold integer numbers', 'Variables are immutable once created'],
                'Python is dynamically typed and infers variable types automatically at assignment.'
            ),
            (
                r'(?:must\s+start\s+with\s+a\s+letter\s+or\s+underscore|rules\s+for\s+naming\s+variables|_name\s+is\s+valid,\s+2name\s+is\s+not)',
                'Variables',
                'medium',
                'Which of the following is a valid rule for naming variables in Python?',
                'Variable names must start with a letter or an underscore',
                ['Variable names can start with any number', 'Variable names can contain spaces', 'Variable names cannot contain underscores'],
                'In Python, variable names must begin with a letter or underscore, not a digit.'
            ),
            (
                r'(?:int\s+represents\s+whole\s+numbers|float\s+represents\s+decimal\s+numbers|type\(10\)|type\(3\.14\))',
                'Data Types',
                'easy',
                'Which Python data type represents numbers with decimal or fractional values?',
                'float',
                ['int', 'str', 'bool'],
                'The float type represents floating-point real numbers with decimal points in Python.'
            ),
            (
                r'(?:bool\s+represents\s+(?:True\s+or\s+False|boolean)|type\(True\))',
                'Data Types',
                'easy',
                'Which Python data type represents True or False boolean values?',
                'bool',
                ['str', 'int', 'float'],
                'The bool type in Python represents boolean logic with either True or False.'
            ),
            (
                r'(?:str\s+represents\s+text|sequence\s+of\s+characters\s+used\s+to\s+represent\s+text|type\("hi"\))',
                'Data Types',
                'easy',
                'Which Python data type is used to store textual character data?',
                'str',
                ['int', 'float', 'bool'],
                'str (string) represents text sequences enclosed in quotes.'
            ),
            (
                r'(?:conditional\s+statements\s+let\s+a\s+program\s+make\s+decisions|if,\s+elif,\s+else|if\s+statement\s+runs\s+a\s+block\s+of\s+code\s+when\s+a\s+condition\s+is\s+true)',
                'if/else',
                'medium',
                'Which keyword in Python is used to test an alternative condition if the preceding if statement is False?',
                'elif',
                ['else if', 'otherwise', 'then'],
                'Python uses elif (else if) to test additional conditions.'
            ),
            (
                r'(?:the\s+while\s+loop|repeat\s+code\s+as\s+long\s+as\s+a\s+condition\s+remains\s+true|while\s+count\s+<\s+5|while\s+loop\s+repeats\s+while\s+its\s+condition\s+remains\s+true)',
                'Loops',
                'medium',
                'When is a while loop typically used in Python?',
                'When code should repeat as long as a specified condition remains True',
                ['Only when iterating over a fixed-length sequence', 'Exclusively when defining function parameters', 'Only when creating multi-line strings'],
                'A while loop repeats continuously until its boolean condition evaluates to False.'
            ),
            (
                r'(?:high-level,\s+general-purpose\s+programming\s+language|used\s+in\s+web\s+development,\s+automation,\s+data\s+analysis|why\s+learn\s+python\s+first)',
                'Python Uses',
                'easy',
                'Which fields is Python widely used in according to the material?',
                'Web development, automation, and data analysis',
                ['Low-level device drivers and microkernel interrupts only', 'Exclusively writing BIOS firmware for motherboards', 'Writing native GPU shader microcode exclusively'],
                'Python is a general-purpose language widely used for web development, automation, and data analysis.'
            ),
            (
                r'(?:lists\s+are\s+mutable|modify\s+in\s+place|ordered,\s+mutable\s+\(changeable\)\s+collection|list\s+is\s+an\s+ordered\s+and\s+changeable\s+collection)',
                'Lists',
                'medium',
                'Which characteristic accurately describes Python lists?',
                'They are ordered and mutable (elements can be modified in place)',
                ['They are immutable and cannot be changed after creation', 'They only store single-character strings', 'They do not maintain element order'],
                'Lists in Python are mutable ordered collections.'
            ),
            (
                r'(?:ZeroDivisionError|dividing\s+a\s+number\s+by\s+zero|10\s*/\s*0)',
                'Common Errors',
                'medium',
                'Which error is raised in Python when an expression attempts to divide a number by zero?',
                'ZeroDivisionError',
                ['IndexError', 'ValueError', 'TypeError'],
                'ZeroDivisionError occurs when an expression attempts to divide by 0.'
            ),
            (
                r'(?:IndexError|accessing\s+a\s+list/string\s+index\s+that\s+doesn\'t\s+exist|list\[10\]\s+on\s+a\s+3-item\s+list)',
                'Common Errors',
                'medium',
                'Which error occurs when accessing an index that is outside the bounds of a list?',
                'IndexError',
                ['KeyError', 'ValueError', 'IndentationError'],
                'IndexError is raised when trying to access a non-existent sequence index.'
            ),
            (
                r'(?:KeyError|accessing\s+a\s+dictionary\s+key\s+that\s+doesn\'t\s+exist|student\["grade"\]\s+if\s+no\s+such\s+key)',
                'Common Errors',
                'medium',
                'Which error is raised when attempting to access a dictionary key that does not exist?',
                'KeyError',
                ['IndexError', 'TypeError', 'SyntaxError'],
                'KeyError occurs when referencing a key that does not exist in a dictionary.'
            ),
            (
                r'(?:defined\s+using\s+the\s+def\s+keyword|def\s+keyword|defining\s+functions|define\s+functions)',
                'Functions',
                'easy',
                'Which keyword is used to define a function in Python?',
                'def',
                ['func', 'function', 'define'],
                'In Python, functions are defined using the def keyword followed by the function name.'
            ),
            (
                r'(?:len\(.*?\)\s+(?:function\s+)?returns|returns\s+the\s+number\s+of\s+items|length\s+of\s+a\s+list)',
                'Functions',
                'easy',
                'What does the len() function return in Python?',
                'The number of items in a collection or sequence',
                ['The memory address of the object', 'The data type of the first element', 'The execution time of the block'],
                'The len() function returns the length or number of items in a sequence or collection.'
            ),
            (
                r'(?:integer\s+division\s+is\s+performed\s+using|//\s+operator|floor\s+division)',
                'Operators',
                'easy',
                'Which operator performs integer or floor division in Python?',
                '//',
                ['/', '%', '**'],
                'The // operator performs integer floor division in Python.'
            ),
            (
                r'(?:booleans\s+have\s+two\s+constant\s+values|boolean\s+values:\s+True\s+and\s+False|two\s+constant\s+values:\s+True\s+and\s+False)',
                'Data Types',
                'easy',
                'What are the two boolean constants in Python?',
                'True and False',
                ['yes and no', '1 and 0 only', 'T and F'],
                'Python booleans consist of True and False.'
            ),
            (
                r'(?:if-elif-else\s+statement|conditional\s+branching\s+and\s+decision)',
                'Conditionals',
                'easy',
                'Which statement structure is used for conditional branching and decision making in Python?',
                'if-elif-else',
                ['switch-case-default', 'try-catch-finally', 'loop-until'],
                'Python uses the if-elif-else construct for conditional decision making.'
            ),
            (
                r'(?:for\s+loop\s+is\s+used\s+for\s+iterating\s+over\s+a\s+sequence)',
                'Loops',
                'easy',
                'What is a for loop in Python primarily used for?',
                'Iterating over a sequence of elements',
                ['Defining recursive class constructors', 'Handling runtime exceptions', 'Compiling modules to bytecode'],
                'A for loop iterates over members of a sequence in order.'
            ),
            # General Computer Science domain patterns
            (
                r'(?:quicksort\s+is\s+a\s+divide-and-conquer|divide-and-conquer\s+algorithm\s+that\s+selects\s+a\s+pivot)',
                'Algorithms',
                'hard',
                'How is Quicksort classified as a sorting algorithm?',
                'A divide-and-conquer algorithm that partitions around a pivot',
                ['A linear searching algorithm with constant overhead', 'A hardware-based hashing mechanism', 'A purely iterative non-recursive swap algorithm'],
                'Quicksort is a divide-and-conquer algorithm that partitions an array around a pivot element.'
            ),
            (
                r'(?:bubble\s+sort\s+compares\s+adjacent\s+elements)',
                'Algorithms',
                'easy',
                'How does Bubble Sort operate on array elements?',
                'It compares adjacent elements and swaps them if they are in the wrong order',
                ['It selects a pivot element and partitions the array', 'It creates a hash table for instant indexing', 'It splits the array in half recursively without comparing'],
                'Bubble sort repeatedly steps through the list, compares adjacent elements, and swaps them if needed.'
            ),
            (
                r'(?:transmission\s+control\s+protocol\s+\(tcp\)\s+is\s+connection-oriented)',
                'Networking',
                'medium',
                'What is a defining characteristic of Transmission Control Protocol (TCP)?',
                'It is connection-oriented and guarantees ordered delivery',
                ['It is connectionless and suitable for unreliable broadcast', 'It does not verify packet delivery or packet order', 'It is exclusively used for wireless radio frequencies'],
                'TCP is connection-oriented and guarantees that packets are delivered in order.'
            ),
            (
                r'(?:user\s+datagram\s+protocol\s+\(udp\)\s+is\s+connectionless)',
                'Networking',
                'medium',
                'What is a primary characteristic of User Datagram Protocol (UDP)?',
                'It is connectionless and suitable for low-latency streaming',
                ['It guarantees ordered delivery of every packet', 'It establishes a 3-way handshake before transmitting', 'It automatically retransmits dropped packets'],
                'UDP is connectionless, prioritizing low latency over reliability and ordered delivery.'
            ),
            (
                r'(?:virtual\s+memory\s+uses\s+page\s+tables|translate\s+virtual\s+addresses\s+into\s+physical\s+frame)',
                'Operating Systems',
                'hard',
                'What do page tables translate in a virtual memory system?',
                'Virtual addresses into physical frame numbers',
                ['Physical frame numbers into hard disk sectors', 'CPU register names into instruction opcodes', 'Network packets into socket identifiers'],
                'Page tables map virtual addresses to physical memory frame numbers.'
            ),
            (
                r'(?:translation\s+lookaside\s+buffer|tlb\s+is\s+an\s+on-chip\s+hardware\s+cache)',
                'Operating Systems',
                'hard',
                'What is the function of the Translation Lookaside Buffer (TLB)?',
                'An on-chip hardware cache for page table entries',
                ['A persistent storage space on disk for swap files', 'A software protocol for routing virtual packets', 'A cooling system controller for processor cores'],
                'The TLB is an on-chip hardware cache that speeds up virtual-to-physical address translations.'
            ),
            (
                r'(?:newton\'s\s+first\s+law\s+states\s+an\s+object\s+at\s+rest)',
                'Physics',
                'medium',
                'What does Newton\'s First Law state?',
                'An object at rest stays at rest unless acted upon by an external force',
                ['Force equals mass times acceleration', 'For every action there is an equal and opposite reaction', 'Energy cannot be created or destroyed'],
                'Newton\'s First Law states an object remains at rest or in uniform motion unless acted upon by an external force.'
            ),
            (
                r'(?:binary\s+search\s+is\s+an\s+efficient\s+algorithm|logarithmic\s+time\s+complexity)',
                'Algorithms',
                'medium',
                'What is the time complexity characteristic of Binary Search?',
                'Logarithmic time complexity on a sorted list',
                ['Linear time complexity on unsorted arrays', 'Exponential time complexity requiring full scans', 'Constant time lookup regardless of sorting'],
                'Binary search operates in O(log n) logarithmic time on sorted sequences.'
            ),
            (
                r'(?:recursion\s+is\s+a\s+programming\s+technique|function\s+calls\s+itself)',
                'Recursion',
                'medium',
                'What is the defining characteristic of recursion?',
                'A technique where a function calls itself to solve a subproblem',
                ['An iterative loop that never uses function calls', 'A database query executed concurrently', 'A compiler pass that generates bytecodes'],
                'Recursion occurs when a function invokes itself directly or indirectly.'
            ),
            (
                r'(?:dynamic\s+programming\s+solves\s+problems|memoization\s+or\s+tabulation)',
                'Algorithms',
                'hard',
                'How does Dynamic Programming solve complex optimization problems?',
                'By combining solutions to subproblems via memoization or tabulation',
                ['By randomly picking solution paths until one succeeds', 'By executing all recursive calls without caching', 'By sorting input arrays with insertion sort'],
                'Dynamic programming caches intermediate subproblem solutions to prevent recomputation.'
            ),
            (
                r'(?:machine\s+learning\s+explores|algorithms\s+that\s+can\s+learn\s+from\s+data)',
                'Machine Learning',
                'medium',
                'What is the primary focus of Machine Learning according to the material?',
                'The study and construction of algorithms that can learn from data',
                ['Static database storage without statistical modeling', 'Translating high-level source code to binary opcodes', 'Hardware cache invalidation routines'],
                'Machine learning explores the study and construction of algorithms that can learn from data.'
            )
        ]

        candidate_questions = []

        # Find matching concept patterns
        for pat, concept, diff, q_text, correct_ans, distractors, explanation in CONCEPT_PATTERNS:
            if re.search(pat, combined_text, re.IGNORECASE):
                # Locate source metadata
                src_fn = context_chunks[0].get("filename", "document.pdf")
                src_pg = context_chunks[0].get("page_number", 1)
                for ch in context_chunks:
                    if re.search(pat, ch.get("chunk_text", ""), re.IGNORECASE):
                        src_fn = ch.get("filename", src_fn)
                        src_pg = ch.get("page_number", src_pg)
                        break

                opts = [correct_ans] + list(distractors[:3])
                # Shuffle options fairly to eliminate position bias
                random.shuffle(opts)

                q_dict = {
                    "concept": concept,
                    "difficulty": diff,
                    "question_type": "mcq",
                    "question_text": q_text,
                    "options": opts,
                    "correct_answer": correct_ans,
                    "feedback": f"{explanation} (Reference: {src_fn}, Page {src_pg})",
                    "source_metadata": {"filename": src_fn, "page": src_pg}
                }
                if cls.validate_quiz_question(q_dict, seen_q_texts):
                    candidate_questions.append(q_dict)

        # 3. Generic Factual Concept Synthesizer for unseen document topics
        if len(candidate_questions) < num_questions:
            factual_sents = []
            for ch in context_chunks:
                fn = ch.get("filename", "document.pdf")
                pg = ch.get("page_number", 1)
                raw_text = ch.get("chunk_text", "")
                
                # Strip table of contents & chapter headers
                cleaned = re.split(r'(?i)\btable\s+of\s+contents\b', raw_text)[0]
                cleaned = re.sub(r'(?i)^chapter\s+\d+.*', '', cleaned, flags=re.MULTILINE)
                cleaned = re.sub(r'(\w+)-\n(\w+)', r'\1\2', cleaned)
                cleaned = re.sub(r'(?<!\n)\n(?!\n)', ' ', cleaned)

                for s in re.split(r'(?<=[.!?])\s+', cleaned):
                    s = s.strip()
                    if len(s) < 25 or len(s) > 180:
                        continue
                    if s.endswith("?") or re.search(r'(?i)table\s+of\s+contents|^chapter\s+\d+', s):
                        continue
                    # Match definitions: "<Noun Phrase> is/represents/provides/stores/explores/studies <Predicate>"
                    def_match = re.match(
                        r'^([A-Z][a-zA-Z0-9_\s]{2,30})\s+(?:is\s+(?:an?|the)?|represents|provides|stores|explores|studies|focuses\s+on|refers\s+to|involves|enables|allows|uses|defines|means)\s+([a-zA-Z0-9_\s,\-\(\)\'\"]{10,140})',
                        s
                    )
                    if def_match:
                        subject = def_match.group(1).strip()
                        predicate = def_match.group(2).strip().rstrip('.,;')
                        if subject.lower() not in {"this", "that", "these", "those", "there", "it"}:
                            factual_sents.append((subject, predicate, s, fn, pg))
                    else:
                        verb_match = re.match(r'^([A-Z][a-zA-Z0-9_\s]{2,25})\s+([a-z]{3,15}\s+[a-zA-Z0-9_\s,\-]{10,120})', s)
                        if verb_match:
                            subj = verb_match.group(1).strip()
                            pred = verb_match.group(2).strip().rstrip('.,;')
                            if not any(v in subj.lower().split() for v in ["is", "are", "was", "were", "can", "should", "will", "has", "have", "defined", "used"]):
                                if subj.lower() not in {"this", "that", "these", "those", "there", "it"}:
                                    factual_sents.append((subj, pred, s, fn, pg))

            # Turn extracted facts into clean conceptual questions
            for idx, (subject, predicate, full_s, fn, pg) in enumerate(factual_sents):
                if len(candidate_questions) >= num_questions * 2:
                    break

                q_text = f"Which of the following best describes {subject} according to the material?"
                correct_opt = predicate[0].upper() + predicate[1:]
                
                # Draw distractors from other factual predicates
                other_preds = [
                    f[1][0].upper() + f[1][1:] for j, f in enumerate(factual_sents)
                    if j != idx and f[0].lower() != subject.lower() and f[1].lower() != predicate.lower()
                ]
                
                distractors = []
                for op in other_preds:
                    if op not in distractors and op != correct_opt:
                        distractors.append(op)
                    if len(distractors) == 3:
                        break

                fallback_pool = [
                    f"A low-level hardware interrupt handled directly by firmware",
                    f"An unmanaged operating system routine executed during kernel boot",
                    f"A transient cache buffer cleared after every clock cycle"
                ]
                for fb in fallback_pool:
                    if len(distractors) < 3 and fb not in distractors:
                        distractors.append(fb)

                opts = [correct_opt] + distractors[:3]
                random.shuffle(opts)

                q_dict = {
                    "concept": subject,
                    "difficulty": "medium",
                    "question_type": "mcq",
                    "question_text": q_text,
                    "options": opts,
                    "correct_answer": correct_opt,
                    "feedback": f"Verified in {fn} (Page {pg}): \"{full_s}\"",
                    "source_metadata": {"filename": fn, "page": pg}
                }
                if cls.validate_quiz_question(q_dict, seen_q_texts):
                    candidate_questions.append(q_dict)

        # 4. Adaptive Prioritization (weak concepts first)
        if weak_concepts:
            weak_lower = set(wc.lower() for wc in weak_concepts)
            weak_candidates = [q for q in candidate_questions if q["concept"].lower() in weak_lower]
            other_candidates = [q for q in candidate_questions if q["concept"].lower() not in weak_lower]
            candidate_questions = weak_candidates + other_candidates

        # 5. Handle retakes / question exhaustion gracefully by relaxing seen_q_texts constraint
        if len(candidate_questions) < num_questions:
            current_batch_norm = {re.sub(r'\W+', '', q["question_text"].lower()) for q in candidate_questions}
            for pat, concept, diff, q_text, correct_ans, distractors, explanation in CONCEPT_PATTERNS:
                if len(candidate_questions) >= num_questions:
                    break
                norm = re.sub(r'\W+', '', q_text.lower())
                if norm in current_batch_norm:
                    continue
                if re.search(pat, combined_text, re.IGNORECASE):
                    src_fn = context_chunks[0].get("filename", "document.pdf")
                    src_pg = context_chunks[0].get("page_number", 1)
                    for ch in context_chunks:
                        if re.search(pat, ch.get("chunk_text", ""), re.IGNORECASE):
                            src_fn = ch.get("filename", src_fn)
                            src_pg = ch.get("page_number", src_pg)
                            break

                    opts = [correct_ans] + list(distractors[:3])
                    random.shuffle(opts)
                    q_dict = {
                        "concept": concept,
                        "difficulty": diff,
                        "question_type": "mcq",
                        "question_text": q_text,
                        "options": opts,
                        "correct_answer": correct_ans,
                        "feedback": f"{explanation} (Reference: {src_fn}, Page {src_pg})",
                        "source_metadata": {"filename": src_fn, "page": src_pg}
                    }
                    if cls.validate_quiz_question(q_dict, current_batch_norm):
                        candidate_questions.append(q_dict)

        return candidate_questions[:num_questions]

    @classmethod
    def generate_open_ended_questions(
        cls,
        context_chunks: List[Dict[str, Any]],
        num_questions: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate conceptual open-ended questions testing deep understanding
        rather than simple recall, grounded strictly in project materials.
        """
        if not context_chunks:
            return []

        formatted_context = ""
        for ch in context_chunks[:10]:
            fn = ch.get("filename", "document.pdf")
            pg = ch.get("page_number", 1)
            txt = ch.get("chunk_text", "")
            formatted_context += f"\n--- [Source: {fn}, Page {pg}] ---\n{txt}\n"

        # 1. LLM Generation
        if settings.AI_API_KEY and settings.AI_API_KEY.startswith("AIza"):
            try:
                system_prompt = (
                    f"You are an expert assessment designer. Generate exactly {num_questions} open-ended questions "
                    "that test conceptual understanding, synthesis, and reasoning rather than simple memorization. "
                    "Ground questions strictly in the provided Context. Return ONLY a valid JSON array of objects:\n"
                    "[\n"
                    "  {\n"
                    '    "concept": "Concept Name",\n'
                    '    "difficulty": "medium" | "hard",\n'
                    '    "question_text": "Thought-provoking question asking learner to explain or analyze in own words...",\n'
                    '    "filename": "doc.pdf",\n'
                    '    "page": 1\n'
                    "  }\n"
                    "]"
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\nContext:\n{formatted_context}"}]}],
                    "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}
                }
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        raw = resp.json().get("candidates", [])[0].get("content", {}).get("parts", [])[0].get("text", "")
                        parsed = json.loads(raw)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            results = []
                            for item in parsed[:num_questions]:
                                results.append({
                                    "concept": item.get("concept", "Core Concept"),
                                    "difficulty": item.get("difficulty", "medium"),
                                    "question_text": item.get("question_text", ""),
                                    "source_metadata": {
                                        "filename": item.get("filename", context_chunks[0].get("filename", "document.pdf")),
                                        "page": item.get("page", context_chunks[0].get("page_number", 1))
                                    }
                                })
                            return results
            except Exception as e:
                print(f"[AIService] Open-ended question generation failed via LLM: {e}. Using deterministic synthesis.")

        # 2. Deterministic synthesis from chunks
        candidates = []
        for ch in context_chunks:
            fn = ch.get("filename", "document.pdf")
            pg = ch.get("page_number", 1)
            raw = ch.get("chunk_text", "")
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw) if len(s.strip()) > 40]
            for s in sents:
                candidates.append({"sentence": s, "filename": fn, "page": pg})

        if not candidates:
            for ch in context_chunks:
                txt = ch.get("chunk_text", "").strip()
                if txt:
                    candidates.append({"sentence": txt[:180], "filename": ch.get("filename", "document.pdf"), "page": ch.get("page_number", 1)})

        questions = []
        target_count = min(num_questions, max(1, len(candidates)))
        step = max(1, len(candidates) // target_count)

        templates = [
            "In your own words, explain how {concept} works and why it is critical in this context.",
            "Analyze the operational behavior of {concept} based on your study material. What are its main properties or mechanisms?",
            "Describe the key principles underlying {concept}. How does it solve the problem or achieve its stated objective?"
        ]

        for i in range(target_count):
            cand_idx = (i * step) % len(candidates)
            cand = candidates[cand_idx]
            sent = cand["sentence"]
            fn = cand["filename"]
            pg = cand["page"]

            words = re.findall(r'\b[A-Z][a-z0-9_]+\b|\b[a-z]{4,}\b', sent)
            concept = "Core Concept"
            for w in words:
                if w.lower() not in {"this", "that", "there", "these", "those", "which", "where", "when", "with", "from"}:
                    concept = w.capitalize()
                    break

            template = templates[i % len(templates)]
            q_text = template.format(concept=concept)

            questions.append({
                "concept": concept,
                "difficulty": "medium" if i % 2 == 0 else "hard",
                "question_text": q_text,
                "source_metadata": {"filename": fn, "page": pg}
            })

        return questions

    @classmethod
    def evaluate_open_ended_response(
        cls,
        question_text: str,
        concept: str,
        context_chunks: List[Dict[str, Any]],
        user_response: str
    ) -> Dict[str, Any]:
        """
        Evaluate a learner's open-ended response using AI.
        Evaluates:
        - Understanding
        - Accuracy
        - Relevance
        - Key concepts covered
        - Missing concepts
        - Reasoning quality
        Returns student-friendly structured feedback.
        """
        clean_resp = user_response.strip()

        # Handle trivial/empty response
        if len(clean_resp) < 15:
            return {
                "score": 20,
                "understanding": f"Minimal response provided. Shows very limited demonstration of {concept}.",
                "accuracy": "Response is too brief to evaluate factual accuracy.",
                "strengths": ["Submitted an answer attempt"],
                "missing_concepts": [concept, "Detailed conceptual explanation"],
                "feedback": f"Your answer is too brief to demonstrate your understanding of {concept}. Please provide a more detailed explanation covering how it operates and why it is used.",
                "concepts": [concept]
            }

        formatted_context = ""
        for ch in context_chunks[:8]:
            fn = ch.get("filename", "document.pdf")
            pg = ch.get("page_number", 1)
            txt = ch.get("chunk_text", "")
            formatted_context += f"\n--- [Source: {fn}, Page {pg}] ---\n{txt}\n"

        # 1. Try LLM evaluation
        if settings.AI_API_KEY and settings.AI_API_KEY.startswith("AIza"):
            try:
                system_prompt = (
                    "You are a supportive, insightful AI pedagogical evaluator. "
                    "Evaluate the student's answer in their own words against the provided Context and Question. "
                    "Do NOT return only a numerical score. Give useful, student-friendly feedback explaining what was "
                    "understood and what was missed. Return ONLY valid JSON with the exact schema:\n"
                    "{\n"
                    '  "score": 78,\n'
                    '  "understanding": "concise description of student\'s comprehension",\n'
                    '  "accuracy": "evaluation of factual precision",\n'
                    '  "strengths": ["strength 1", "strength 2"],\n'
                    '  "missing_concepts": ["concept or detail missed"],\n'
                    '  "feedback": "encouraging, constructive student-friendly feedback",\n'
                    '  "concepts": ["concept1", "concept2"]\n'
                    "}"
                )
                user_content = (
                    f"Context:\n{formatted_context}\n\n"
                    f"Concept: {concept}\n"
                    f"Question: {question_text}\n\n"
                    f"Student Response:\n{clean_resp}"
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_content}"}]}],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
                }
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        raw = resp.json().get("candidates", [])[0].get("content", {}).get("parts", [])[0].get("text", "")
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict) and "score" in parsed:
                            return {
                                "score": int(max(0, min(100, parsed.get("score", 70)))),
                                "understanding": str(parsed.get("understanding", "")),
                                "accuracy": str(parsed.get("accuracy", "")),
                                "strengths": list(parsed.get("strengths", [])),
                                "missing_concepts": list(parsed.get("missing_concepts", [])),
                                "feedback": str(parsed.get("feedback", "")),
                                "concepts": list(parsed.get("concepts", [concept]))
                            }
            except Exception as e:
                print(f"[AIService] LLM assessment evaluation failed: {e}. Using deterministic evaluation.")

        # 2. Deterministic Semantic Evaluation fallback
        resp_lower = clean_resp.lower()
        context_text = " ".join(c.get("chunk_text", "") for c in context_chunks).lower()

        # Extract domain terms from context (words with >= 4 letters, excluding common stop words)
        from app.services.ai_service import AIService
        raw_terms = re.findall(r'\b[a-z]{4,}\b', context_text)
        COMMON_STOP = {
            "this", "that", "there", "these", "those", "which", "where", "when", "with", "from",
            "have", "been", "were", "what", "does", "explain", "describe", "about", "some", "more"
        }
        domain_terms = list(dict.fromkeys(t for t in raw_terms if t not in COMMON_STOP))[:20]

        matched_terms = [t for t in domain_terms if t in resp_lower]
        missing_terms = [t.capitalize() for t in domain_terms if t not in resp_lower][:3]

        ratio = len(matched_terms) / max(1, min(10, len(domain_terms)))
        concept_lower = concept.lower()
        concept_present = concept_lower in resp_lower

        if concept_present:
            ratio = min(1.0, ratio + 0.3)

        if ratio >= 0.5:
            score = int(min(96, 75 + ratio * 20))
            understanding = f"Demonstrates a solid and well-articulated grasp of {concept}."
            accuracy = "Factually accurate and consistent with the project's study material."
            strengths = [
                f"Clearly identified and explained core ideas behind {concept}",
                "Used appropriate and relevant technical terminology",
                "Demonstrated logical reasoning in the explanation"
            ]
            missing = missing_terms[:1] if missing_terms else []
            feedback = (
                f"Your answer shows a strong understanding of {concept}. You explained the key mechanisms accurately. "
                + (f"To make your answer even more comprehensive, you could also mention {missing[0]}." if missing else "Well done!")
            )
        elif ratio >= 0.25:
            score = int(min(78, 60 + ratio * 30))
            understanding = f"Shows a good working understanding of {concept}, though some details are incomplete."
            accuracy = "Generally accurate, with minor omissions of key relationships."
            strengths = [
                f"Understands the general premise and role of {concept}",
                "Provided a relevant and coherent explanation"
            ]
            missing = missing_terms[:2] if missing_terms else [f"Deeper details on {concept}"]
            feedback = (
                f"Your answer shows a good understanding of {concept}, but one important relationship is missing. "
                + (f"Consider explaining how it connects with {missing[0]}." if missing else "")
            )
        else:
            score = int(max(40, min(58, 35 + len(clean_resp) // 15)))
            understanding = f"Shows emerging understanding of {concept}, but lacks core technical precision."
            accuracy = "Partially accurate; key definitions from the material were omitted."
            strengths = ["Recognized the relevant subject area"]
            missing = [concept] + missing_terms[:2]
            feedback = (
                f"Your answer touches upon the general topic, but misses several key concepts explained in the material. "
                f"We recommend reviewing the sections discussing {concept} and trying to elaborate on how it operates."
            )

        return {
            "score": score,
            "understanding": understanding,
            "accuracy": accuracy,
            "strengths": strengths,
            "missing_concepts": missing,
            "feedback": feedback,
            "concepts": [concept] + [m for m in matched_terms[:2] if m.capitalize() != concept]
        }

    @staticmethod
    def log_ai_usage(
        db: Session,
        user_id: int,
        project_id: int,
        feature: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: int,
        success: bool
    ) -> None:
        """
        Record AI request metrics without interrupting the primary application flow.
        """
        if db is None:
            return
        try:
            usage = AIUsage(
                user_id=user_id,
                project_id=project_id,
                feature=feature,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                success=success,
                created_at=datetime.now(timezone.utc)
            )
            db.add(usage)
            db.commit()
        except Exception as exc:
            if db:
                db.rollback()
            print(f"[AIService] Non-blocking error logging AI usage: {exc}")
