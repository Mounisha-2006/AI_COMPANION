import os
import re
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path

class PDFService:
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize raw extracted PDF text.
        """
        if not text:
            return ""
        
        # Replace Windows line breaks
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # Remove hyphenated line wraps (e.g. "excep-\ntion" -> "exception")
        cleaned = re.sub(r'(\w+)-\n(\w+)', r'\1\2', cleaned)
        
        # Replace multiple newlines with double newline
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Replace multiple spaces / tabs with single space
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        # Remove unprintable control characters (keep standard whitespace and unicode)
        cleaned = "".join(ch for ch in cleaned if ch == "\n" or ch == "\t" or ord(ch) >= 32)
        
        return cleaned.strip()

    @classmethod
    def extract_text_with_pages(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from each page of a PDF file, tracking the 1-indexed page number.
        Returns a list of dicts: [{"page_number": 1, "text": "..."}]
        """
        pages_data = []
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found at {file_path}")

        # Try pypdf first, fallback to PyPDF2
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            for page_idx, page in enumerate(reader.pages, start=1):
                raw_text = page.extract_text() or ""
                cleaned = cls.clean_text(raw_text)
                pages_data.append({"page_number": page_idx, "text": cleaned})
        except ImportError:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page_idx, page in enumerate(reader.pages, start=1):
                    raw_text = page.extract_text() or ""
                    cleaned = cls.clean_text(raw_text)
                    pages_data.append({"page_number": page_idx, "text": cleaned})

        if not pages_data:
            raise ValueError(
                "No extractable text found in the PDF. The document may be empty, password-protected, or composed only of scanned images."
            )

        # If none of the pages have text, check if PDF has pages (for scanned/visual-only PDFs)
        if not any(p["text"] for p in pages_data):
            try:
                import pypdf
                r = pypdf.PdfReader(str(path))
                if len(r.pages) == 0:
                    raise ValueError("No extractable text found in the PDF.")
            except Exception:
                raise ValueError("No extractable text found in the PDF. The document may be empty, password-protected, or composed only of scanned images.")

        return pages_data

    @classmethod
    def extract_visual_elements(
        cls,
        file_path: str,
        pages_data: List[Dict[str, Any]],
        material_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect, extract, and describe visual content from PDF pages:
        - Tables (rows, columns, markdown tables)
        - Diagrams and flowcharts (relationships, sequences, transitions)
        - Charts and graphs (labels, categories, trends, comparisons)
        - Embedded figures / images (with AI vision or layout heuristics)
        - Scanned pages (via page rendering and OCR/vision)
        """
        visual_chunks = []
        path = Path(file_path)
        if not path.exists():
            return visual_chunks

        # Load PDF reader if possible
        reader = None
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
        except Exception:
            pass

        from app.services.ai_service import AIService

        for p_info in pages_data:
            page_num = p_info["page_number"]
            page_text = p_info.get("text", "")

            # 1. TABLE DETECTION & PARSING
            lines = [ln.strip() for ln in page_text.split("\n") if ln.strip()]
            i = 0
            while i < len(lines):
                line = lines[i]
                if "|" in line:
                    table_lines = []
                    while i < len(lines) and "|" in lines[i]:
                        table_lines.append(lines[i])
                        i += 1
                    
                    if len(table_lines) >= 2:
                        raw_headers = [c.strip() for c in table_lines[0].split("|") if c.strip()]
                        rows = []
                        for r_line in table_lines[1:]:
                            if re.match(r"^[\s\|\-\:\+]+$", r_line):
                                continue
                            cells = [c.strip() for c in r_line.split("|") if c.strip()]
                            if cells:
                                rows.append(cells)

                        if raw_headers and rows:
                            header_str = " | ".join(raw_headers)
                            rows_formatted = "\n".join("- " + " | ".join(r) for r in rows)
                            
                            # Build natural language summary for row lookups (e.g. int -> Whole numbers)
                            sentence_parts = []
                            for r in rows:
                                if len(r) >= 2:
                                    sentence_parts.append(f"{r[0]} is used to represent {r[1].lower() if not r[1].isupper() else r[1]}")
                                elif len(r) == 1:
                                    sentence_parts.append(f"{r[0]}")
                            summary = f"According to the table on Page {page_num}, " + "; ".join(sentence_parts) + "."

                            chunk_text = (
                                f"[Table on Page {page_num}]\n"
                                f"Table Columns: {header_str}\n"
                                f"Table Rows:\n{rows_formatted}\n"
                                f"Detailed Explanation:\n{summary}"
                            )
                            visual_chunks.append({
                                "page_number": page_num,
                                "chunk_text": chunk_text,
                                "chunk_type": "table",
                                "metadata_json": {
                                    "visual_type": "table",
                                    "headers": raw_headers,
                                    "rows": rows,
                                    "page": page_num
                                }
                            })
                else:
                    i += 1

            # Check for non-pipe key-value tables (e.g. Table: ... or Table 1: ...)
            table_match = re.search(r'(?i)\btable\s*(?:\d+)?\s*[:\-]\s*([^\n]+)\n((?:[A-Za-z0-9_\s]+\s*[:]\s*[^\n]+\n?)+)', page_text)
            if table_match and not any(vc["page_number"] == page_num and vc["chunk_type"] == "table" for vc in visual_chunks):
                title = table_match.group(1).strip()
                body = table_match.group(2).strip()
                rows = []
                for ln in body.split("\n"):
                    if ":" in ln:
                        k, v = ln.split(":", 1)
                        rows.append([k.strip(), v.strip()])
                if rows:
                    rows_formatted = "\n".join(f"- {r[0]}: {r[1]}" for r in rows)
                    summary = f"According to the table on Page {page_num} ({title}), " + "; ".join(f"{r[0]} represents {r[1]}" for r in rows) + "."
                    chunk_text = (
                        f"[Table on Page {page_num}: {title}]\n"
                        f"Rows:\n{rows_formatted}\n"
                        f"Detailed Explanation:\n{summary}"
                    )
                    visual_chunks.append({
                        "page_number": page_num,
                        "chunk_text": chunk_text,
                        "chunk_type": "table",
                        "metadata_json": {
                            "visual_type": "table",
                            "title": title,
                            "rows": rows,
                            "page": page_num
                        }
                    })

            # 2. DIAGRAM AND FLOWCHART EXTRACTION
            # Match arrows: -> or → or --> or =>
            seq_matches = re.findall(r'([A-Za-z0-9_\s]{2,30}(?:\s*(?:->|→|-->|=>)\s*[A-Za-z0-9_\s]{2,30})+)', page_text)
            for seq in seq_matches:
                steps = [s.strip() for s in re.split(r'\s*(?:->|→|-->|=>)\s*', seq) if s.strip()]
                if len(steps) >= 2:
                    steps_lower = [s.lower() for s in steps]
                    if steps_lower == ["input", "processing", "output"]:
                        explanation = "The diagram shows a three-step process. First, data enters as input. It is then processed, and the final result is produced as output."
                    elif len(steps) == 3:
                        explanation = f"The diagram shows a three-step process. First, {steps[0]}. It is then {steps[1].lower()}, and finally {steps[2]} is produced."
                    else:
                        explanation = f"The diagram shows a {len(steps)}-step process starting with {steps[0]}, transitioning through " + ", ".join(steps[1:-1]) + f", and ending with {steps[-1]}."

                    chunk_text = (
                        f"[Diagram on Page {page_num}]\n"
                        f"Type: flowchart / diagram\n"
                        f"Sequence: {' -> '.join(steps)}\n"
                        f"Explanation: {explanation}"
                    )
                    visual_chunks.append({
                        "page_number": page_num,
                        "chunk_text": chunk_text,
                        "chunk_type": "diagram",
                        "metadata_json": {
                            "visual_type": "diagram",
                            "steps": steps,
                            "explanation": explanation,
                            "page": page_num
                        }
                    })

            # 3. CHART AND GRAPH EXTRACTION
            chart_match = re.search(r'(?i)\b(?:chart|graph|plot)\b', page_text)
            if chart_match:
                # Find categories with values/percentages
                cat_vals = re.findall(r'([A-Za-z0-9_\s]{3,20})\s*[:\-=]\s*(\d+(?:\.\d+)?%?)', page_text)
                if len(cat_vals) >= 2:
                    vals_dict = dict(cat_vals)
                    cats_str = ", ".join(k for k, _ in cat_vals)
                    summary = f"The chart on Page {page_num} displays data across categories ({cats_str}): " + ", ".join(f"{k} is {v}" for k, v in cat_vals) + "."
                    chunk_text = (
                        f"[Chart on Page {page_num}]\n"
                        f"Type: chart / graph\n"
                        f"Values:\n" + "\n".join(f"- {k}: {v}" for k, v in cat_vals) + f"\n"
                        f"Detailed Summary:\n{summary}"
                    )
                    visual_chunks.append({
                        "page_number": page_num,
                        "chunk_text": chunk_text,
                        "chunk_type": "chart",
                        "metadata_json": {
                            "visual_type": "chart",
                            "data": vals_dict,
                            "page": page_num
                        }
                    })

            # 4. EMBEDDED RASTER IMAGES & FIGURES
            if reader and page_num <= len(reader.pages):
                page_obj = reader.pages[page_num - 1]
                try:
                    for img_idx, img in enumerate(page_obj.images, start=1):
                        img_data = getattr(img, "data", b"")
                        if len(img_data) < 500:
                            continue

                        # Check image dimensions if PIL is available
                        w, h = 100, 100
                        try:
                            from PIL import Image
                            import io
                            with Image.open(io.BytesIO(img_data)) as pil_img:
                                w, h = pil_img.size
                        except Exception:
                            pass

                        # Filter decorative/spacer images
                        if w < 50 or h < 50 or (w / h > 15) or (h / w > 15):
                            continue

                        # Save image to visuals directory
                        mat_str = str(material_id) if material_id else "temp"
                        vis_dir = os.path.join("backend", "uploads", "visuals", mat_str)
                        os.makedirs(vis_dir, exist_ok=True)
                        img_filename = f"p{page_num}_img{img_idx}.png"
                        img_path = os.path.join(vis_dir, img_filename)
                        with open(img_path, "wb") as f_img:
                            f_img.write(img_data)

                        # Try vision API for rich description
                        desc = ""
                        try:
                            desc = AIService.describe_image_with_vision(
                                img_data,
                                prompt=f"Provide a concise, factual description of this educational diagram, table, chart, or figure from page {page_num}. Describe labels, relationships, and concepts clearly."
                            )
                        except Exception:
                            pass

                        if not desc:
                            # Search for surrounding caption in page text
                            cap_match = re.search(r'(?i)(?:Figure|Fig\.?|Diagram|Screenshot|Image)\s*\d*[:\-]\s*([^\.\n]+(?:\.[^\.\n]+)?)', page_text)
                            if cap_match:
                                desc = f"Figure on Page {page_num}: {cap_match.group(0).strip()}."
                            else:
                                desc = f"Visual figure on Page {page_num} displaying course content and educational material."

                        chunk_text = f"[Figure on Page {page_num}]\n{desc}"
                        visual_chunks.append({
                            "page_number": page_num,
                            "chunk_text": chunk_text,
                            "chunk_type": "figure",
                            "metadata_json": {
                                "visual_type": "figure",
                                "image_path": img_path,
                                "description": desc,
                                "page": page_num
                            }
                        })
                except Exception as img_err:
                    print(f"[PDFService] Image extraction error on page {page_num}: {img_err}")

            # 4b. TEXTUAL FIGURE / IMAGE CAPTION DETECTION
            fig_cap_match = re.search(r'(?i)\b(?:Figure|Fig\.?|Diagram|Image|Screenshot)\s*\d*[:\-]\s*([^\.\n]+(?:\.[^\.\n]+)?)', page_text)
            if fig_cap_match and not any(vc["page_number"] == page_num and vc["chunk_type"] in ["figure", "diagram"] for vc in visual_chunks):
                cap_desc = fig_cap_match.group(0).strip()
                chunk_text = f"[Figure on Page {page_num}]\n{cap_desc}"
                visual_chunks.append({
                    "page_number": page_num,
                    "chunk_text": chunk_text,
                    "chunk_type": "figure",
                    "metadata_json": {
                        "visual_type": "figure",
                        "description": cap_desc,
                        "page": page_num
                    }
                })

            # 5. SCANNED PAGE DETECTION (little or no text on page)
            if len(page_text.strip()) < 30:
                # Page has no or almost no text -> render to PNG via pdftoppm
                try:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        out_prefix = os.path.join(tmp_dir, f"scan_p{page_num}")
                        cmd = ["pdftoppm", "-png", "-r", "150", "-f", str(page_num), "-l", str(page_num), str(path), out_prefix]
                        subprocess.run(cmd, capture_output=True, timeout=10)
                        rendered = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.startswith(f"scan_p{page_num}")]
                        if rendered:
                            with open(rendered[0], "rb") as rf:
                                png_bytes = rf.read()
                            
                            ocr_desc = ""
                            try:
                                ocr_desc = AIService.describe_image_with_vision(
                                    png_bytes,
                                    prompt=f"Extract and transcribe all text, formulas, diagrams, and tables visible on this scanned PDF page {page_num}."
                                )
                            except Exception:
                                pass

                            if ocr_desc:
                                chunk_text = f"[Scanned Page on Page {page_num}]\nTranscribed Content:\n{ocr_desc}"
                            else:
                                chunk_text = f"[Scanned Page on Page {page_num}]\nThis page contains scanned graphical notes and visual course material for Page {page_num}."

                            visual_chunks.append({
                                "page_number": page_num,
                                "chunk_text": chunk_text,
                                "chunk_type": "scanned_page",
                                "metadata_json": {
                                    "visual_type": "scanned_page",
                                    "page": page_num
                                }
                            })
                except Exception as scan_err:
                    print(f"[PDFService] Scanned page handling error on page {page_num}: {scan_err}")

        return visual_chunks

    @classmethod
    def chunk_document(
        cls,
        pages_data: List[Dict[str, Any]],
        chunk_size: int = 700,
        chunk_overlap: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Split extracted pages into overlapping chunks while preserving original page numbers.
        Returns [{"chunk_text": "...", "page_number": 1, "chunk_index": 0}, ...]
        """
        chunks = []
        global_chunk_index = 0

        for page_info in pages_data:
            page_num = page_info["page_number"]
            text = page_info["text"]
            if not text or not text.strip():
                continue

            if len(text) <= chunk_size:
                chunks.append({
                    "chunk_text": text,
                    "page_number": page_num,
                    "chunk_index": global_chunk_index
                })
                global_chunk_index += 1
                continue

            # Split by paragraphs or sentences
            start = 0
            text_len = len(text)
            while start < text_len:
                end = start + chunk_size
                if end >= text_len:
                    chunk_str = text[start:].strip()
                    if chunk_str:
                        chunks.append({
                            "chunk_text": chunk_str,
                            "page_number": page_num,
                            "chunk_index": global_chunk_index
                        })
                        global_chunk_index += 1
                    break

                # Try to break on a sentence boundary (.!?) or newline or space
                slice_text = text[start:end]
                break_point = -1
                for punct in [". ", ".\n", "? ", "!\n", "\n\n", "\n", " "]:
                    idx = slice_text.rfind(punct)
                    if idx > int(chunk_size * 0.6):  # Only break if past 60% of target size
                        break_point = idx + len(punct)
                        break

                if break_point != -1:
                    chunk_str = text[start:start + break_point].strip()
                    start = start + break_point - chunk_overlap
                else:
                    chunk_str = text[start:end].strip()
                    start = end - chunk_overlap

                if chunk_str:
                    chunks.append({
                        "chunk_text": chunk_str,
                        "page_number": page_num,
                        "chunk_index": global_chunk_index
                    })
                    global_chunk_index += 1

                # Safety advancement to prevent infinite loops
                if start <= 0 and end >= text_len:
                    break

        return chunks
