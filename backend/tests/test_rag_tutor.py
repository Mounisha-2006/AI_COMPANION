import io
import time
from fpdf import FPDF
from app.services.pdf_service import PDFService
from app.services.retrieval_service import RetrievalService
from app.models.document_chunk import DocumentChunk
from app.models.material import Material, MaterialStatus

def make_sample_pdf(pages_text):
    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(w=0, h=10, text=text)
    return bytes(pdf.output())

def test_pdf_extraction_preserves_pages():
    pages_content = [
        "Page One: The central processing unit (CPU) executes instructions fetched from memory.",
        "Page Two: Paging is a memory management scheme that eliminates the need for contiguous physical memory.",
        "Page Three: Thrashing occurs when a computer's virtual memory resources are overused."
    ]
    pdf_bytes = make_sample_pdf(pages_content)
    
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        path = f.name

    try:
        pages = PDFService.extract_text_with_pages(path)
        assert len(pages) == 3
        assert pages[0]["page_number"] == 1
        assert "CPU" in pages[0]["text"]
        assert pages[1]["page_number"] == 2
        assert "Paging" in pages[1]["text"]
        assert pages[2]["page_number"] == 3
        assert "Thrashing" in pages[2]["text"]

        chunks = PDFService.chunk_document(pages, chunk_size=300)
        assert len(chunks) >= 3
        assert all("page_number" in c for c in chunks)
        assert any(c["page_number"] == 1 for c in chunks)
        assert any(c["page_number"] == 2 for c in chunks)
        assert any(c["page_number"] == 3 for c in chunks)
    finally:
        os.remove(path)

def test_material_processing_creates_chunks(client, user_a_headers, db_session):
    # Setup space & project
    space = client.post("/spaces", headers=user_a_headers, json={"name": "CS Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={
        "name": "Operating Systems",
        "learning_goal": "Understand memory and paging"
    }).json()
    proj_id = proj["id"]

    # Upload PDF with 2 distinct pages
    pdf_data = make_sample_pdf([
        "Virtual memory uses page tables to translate virtual addresses into physical frame numbers.",
        "The Translation Lookaside Buffer or TLB is an on-chip hardware cache for page table entries."
    ])
    files = {"file": ("os_memory.pdf", io.BytesIO(pdf_data), "application/pdf")}
    res = client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)
    assert res.status_code == 201
    mat_id = res.json()["id"]

    # In TestClient, BackgroundTasks run during the request
    # Verify material is ready
    mat_res = client.get(f"/materials/{mat_id}", headers=user_a_headers)
    assert mat_res.status_code == 200
    assert mat_res.json()["status"] == "ready"

    # Verify chunks exist in DB
    chunks = db_session.query(DocumentChunk).filter(DocumentChunk.material_id == mat_id).all()
    assert len(chunks) >= 2
    assert any("Virtual memory" in c.chunk_text for c in chunks)
    assert any("Translation Lookaside Buffer" in c.chunk_text for c in chunks)
    assert all(c.embedding is not None for c in chunks)
    assert all(len(c.embedding) > 0 for c in chunks)

def test_project_scoped_retrieval(client, user_a_headers, db_session):
    # Setup space & project
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Networking"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Protocols"}).json()
    proj_id = proj["id"]

    # Upload networking PDF
    pdf_data = make_sample_pdf([
        "Transmission Control Protocol (TCP) is connection-oriented and guarantees ordered delivery.",
        "User Datagram Protocol (UDP) is connectionless and suitable for low-latency streaming."
    ])
    files = {"file": ("transport_protocols.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    user_a_id = client.get("/auth/me", headers=user_a_headers).json()["id"]

    # Search for TCP
    tcp_chunks = RetrievalService.search_project_chunks(
        db=db_session,
        project_id=proj_id,
        user_id=user_a_id,
        query="What is Transmission Control Protocol TCP?",
        top_k=2
    )
    assert len(tcp_chunks) > 0
    assert "TCP" in tcp_chunks[0]["chunk_text"]
    assert tcp_chunks[0]["page_number"] == 1
    assert tcp_chunks[0]["filename"] == "transport_protocols.pdf"

def test_cross_project_and_user_isolation(client, user_a_headers, user_b_headers, db_session):
    user_a_id = client.get("/auth/me", headers=user_a_headers).json()["id"]
    user_b_id = client.get("/auth/me", headers=user_b_headers).json()["id"]

    # User A creates Project A1 and uploads secret material
    space_a = client.post("/spaces", headers=user_a_headers, json={"name": "User A Space"}).json()
    proj_a1 = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={"name": "Project A1"}).json()
    
    # User A creates Project A2
    proj_a2 = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={"name": "Project A2"}).json()

    pdf_a1 = make_sample_pdf(["Confidential project A1 data regarding quantum cryptography algorithms."])
    files = {"file": ("secret_a1.pdf", io.BytesIO(pdf_a1), "application/pdf")}
    client.post(f"/projects/{proj_a1['id']}/materials", headers=user_a_headers, files=files)

    # User B creates Project B
    space_b = client.post("/spaces", headers=user_b_headers, json={"name": "User B Space"}).json()
    proj_b = client.post(f"/spaces/{space_b['id']}/projects", headers=user_b_headers, json={"name": "Project B"}).json()

    # 1. Project A2 searches for quantum cryptography -> should find NOTHING (Project-level isolation)
    a2_chunks = RetrievalService.search_project_chunks(
        db=db_session,
        project_id=proj_a2["id"],
        user_id=user_a_id,
        query="quantum cryptography"
    )
    assert len(a2_chunks) == 0

    # 2. User B searches Project B -> should find NOTHING
    b_chunks = RetrievalService.search_project_chunks(
        db=db_session,
        project_id=proj_b["id"],
        user_id=user_b_id,
        query="quantum cryptography"
    )
    assert len(b_chunks) == 0


    # 3. User B tries to chat on User A's Project A1 -> 404
    tutor_hack = client.post(f"/projects/{proj_a1['id']}/tutor/chat", headers=user_b_headers, json={
        "message": "What is the confidential quantum cryptography algorithm?"
    })
    assert tutor_hack.status_code == 404

def test_ai_tutor_grounded_answer_and_citations(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Algorithms"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Sorting"}).json()
    proj_id = proj["id"]

    pdf_data = make_sample_pdf([
        "Page 1: Bubble sort compares adjacent elements and swaps them if they are in the wrong order.",
        "Page 2: Quicksort is a divide-and-conquer algorithm that selects a pivot element and partitions the array."
    ])
    files = {"file": ("sorting_guide.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    # Ask question supported by Page 2
    chat_res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "How does quicksort work?"
    })
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert data["grounded"] is True
    assert len(data["sources"]) > 0
    # Cites sorting_guide.pdf on Page 2
    assert any(s["filename"] == "sorting_guide.pdf" and s["page"] == 2 for s in data["sources"])
    assert "quicksort" in data["answer"].lower() or "divide" in data["answer"].lower() or "pivot" in data["answer"].lower()

def test_ai_tutor_unsupported_question_rejection(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "History"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Ancient Rome"}).json()
    proj_id = proj["id"]

    pdf_data = make_sample_pdf([
        "Julius Caesar crossed the Rubicon in 49 BC, precipitating the Roman civil war."
    ])
    files = {"file": ("rome.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    # Ask completely unrelated question
    unrelated_res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "What is the recipe to bake sourdough bread with yeast?"
    })
    assert unrelated_res.status_code == 200
    data = unrelated_res.json()
    # Must NOT hallucinate sourdough recipe
    assert "couldn't find" in data["answer"].lower() or "not available in the uploaded material" in data["answer"].lower()
    assert data["grounded"] is False
    assert len(data["sources"]) == 0

def test_tutor_conversation_history_endpoints(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Physics"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Mechanics"}).json()
    proj_id = proj["id"]

    pdf_data = make_sample_pdf([
        "Newton's First Law states an object at rest stays at rest unless acted upon by an external force."
    ])
    files = {"file": ("physics1.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    # Ask question
    client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "What is Newton's First Law?"
    })

    # Fetch history
    hist_res = client.get(f"/projects/{proj_id}/tutor/history", headers=user_a_headers)
    assert hist_res.status_code == 200
    messages = hist_res.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert "Newton" in messages[0]["content"]
    assert messages[1]["role"] == "assistant"

    # Clear history
    del_res = client.delete(f"/projects/{proj_id}/tutor/history", headers=user_a_headers)
    assert del_res.status_code == 204

    # Verify cleared
    empty_hist = client.get(f"/projects/{proj_id}/tutor/history", headers=user_a_headers).json()
    assert len(empty_hist) == 0

def test_ai_tutor_list_first_index_answer(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Programming"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Python 101"}).json()
    proj_id = proj["id"]

    pdf_data = make_sample_pdf([
        "Python Basics: Python is used in web development, automation, and data analysis.\nCommon Data Types: int represents whole numbers, str represents text, bool represents boolean.",
        "Lists: A list is an ordered collection. List elements are accessed using indexes, and Python indexes start at 0. Example: numbers = [10, 20, 30], numbers[0] gives 10.\n\nQuick Review Questions:\n1. What is Python used for?\n2. Name four Python data types.\n3. What is the first index of a Python list?"
    ])
    files = {"file": ("Python_Basics_Test.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    # 1. Ask single question: "What is the first index of a Python list?"
    res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "What is the first index of a Python list?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert data["answer"], "Expected answer to exist"
    # The answer MUST contain '0'
    assert "0" in data["answer"], f"Expected '0' in answer, got: {data['answer']}"
    # Must NOT simply echo the review question
    assert not data["answer"].strip().endswith("?")
    assert "what is the first index" not in data["answer"].lower()
    # Must NOT start with 'Based on the course material'
    assert not data["answer"].lower().startswith("based on the course material")
    # Must NOT equal retrieved context or document title/heading
    assert data["answer"] != pdf_data
    assert "python basics" not in data["answer"].lower() or "first index" in data["answer"].lower()
    # Must cite Page 2 of Python_Basics_Test.pdf
    assert len(data["sources"]) > 0
    assert any(s["filename"] == "Python_Basics_Test.pdf" and s["page"] == 2 for s in data["sources"])

    # 2. Ask multi-part question: "What is Python used for? Name four Python data types. What is the first index of a Python list?"
    multi_res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "What is Python used for? Name four Python data types. What is the first index of a Python list?"
    })
    assert multi_res.status_code == 200
    m_data = multi_res.json()
    assert m_data["grounded"] is True
    assert "0" in m_data["answer"], f"Expected '0' in multi-answer, got: {m_data['answer']}"
    assert not m_data["answer"].strip().endswith("?")
    assert not m_data["answer"].lower().startswith("based on the course material")
    assert len(m_data["sources"]) >= 1

def test_multimodal_pdf_visual_extraction():
    import tempfile, os
    pdf = FPDF()
    # Page 1: Text
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(w=0, h=10, text="Intro to algorithms and system architectures.")

    # Page 2: Table
    pdf.add_page()
    pdf.multi_cell(w=0, h=10, text="| Data Type | Description |\n| int | whole numbers |\n| str | textual data |")

    # Page 3: Diagram
    pdf.add_page()
    pdf.multi_cell(w=0, h=10, text="Pipeline Workflow:\nInput -> Processing -> Output")

    # Page 4: Chart
    pdf.add_page()
    pdf.multi_cell(w=0, h=10, text="Quarterly Metrics Chart:\nQ1 : 120\nQ2 : 240\nQ3 : 360")

    # Page 5: Scanned/empty page
    pdf.add_page()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(bytes(pdf.output()))
        path = f.name

    try:
        pages = PDFService.extract_text_with_pages(path)
        assert len(pages) == 5
        visual_chunks = PDFService.extract_visual_elements(path, pages)
        types = [vc["chunk_type"] for vc in visual_chunks]
        assert "table" in types
        assert "diagram" in types
        assert "chart" in types
        assert "scanned_page" in types

        # Check table chunk metadata
        tbl = next(vc for vc in visual_chunks if vc["chunk_type"] == "table")
        assert tbl["page_number"] == 2
        assert tbl["metadata_json"]["visual_type"] == "table"

        # Check diagram chunk metadata
        dia = next(vc for vc in visual_chunks if vc["chunk_type"] == "diagram")
        assert dia["page_number"] == 3
        assert "three-step process" in dia["chunk_text"]

        # Check chart chunk metadata
        ch = next(vc for vc in visual_chunks if vc["chunk_type"] == "chart")
        assert ch["page_number"] == 4
        assert "Q1" in ch["chunk_text"]
    finally:
        os.remove(path)

def test_ai_tutor_visual_table_understanding(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Data Structures"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Type Reference"}).json()
    proj_id = proj["id"]

    pdf_data = make_sample_pdf([
        "Python Overview: High level general purpose language.",
        "Data Types Reference:\n| Data Type | Description |\n| int | whole numbers |\n| str | textual characters |\n| float | decimal numbers |"
    ])
    files = {"file": ("data_types_table.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "What does the table say about int?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert "whole numbers" in data["answer"].lower() or "int" in data["answer"].lower()
    assert len(data["sources"]) > 0
    assert any(s["page"] == 2 and s.get("visual_type") == "table" for s in data["sources"])

def test_ai_tutor_visual_diagram_flowchart(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "System Design"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Pipelines"}).json()
    proj_id = proj["id"]

    pdf_data = make_sample_pdf([
        "Introduction: System design concepts and patterns.",
        "Execution Architecture Diagram:\nInput -> Processing -> Output"
    ])
    files = {"file": ("architecture_diagram.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "Explain this diagram."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert "three-step process" in data["answer"].lower() or ("input" in data["answer"].lower() and "output" in data["answer"].lower())
    assert len(data["sources"]) > 0
    assert any(s["page"] == 2 and s.get("visual_type") == "diagram" for s in data["sources"])

def test_ai_tutor_visual_chart_understanding(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Analytics Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Metrics Project"}).json()
    proj_id = proj["id"]

    pdf_data = make_sample_pdf([
        "Annual performance report introduction.",
        "Quarterly Sales Chart:\nQ1 : 100\nQ2 : 250\nQ3 : 400"
    ])
    files = {"file": ("sales_chart.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "Explain the chart."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert "q1" in data["answer"].lower() or "q2" in data["answer"].lower() or "chart" in data["answer"].lower()
    assert len(data["sources"]) > 0
    assert any(s["page"] == 2 and s.get("visual_type") == "chart" for s in data["sources"])

def test_ai_tutor_visual_scanned_page(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Scanned Material"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "History Notes"}).json()
    proj_id = proj["id"]

    # Page 1 has text, Page 2 is empty (scanned page)
    pdf_data = make_sample_pdf([
        "Introduction to Ancient Architecture notes.",
        ""
    ])
    files = {"file": ("scanned_notes.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "What is on page 2?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert len(data["sources"]) > 0
    assert any(s["page"] == 2 and s.get("visual_type") == "scanned_page" for s in data["sources"])

def test_ai_tutor_multipart_text_and_visual(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Full Stack"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Python Guide"}).json()
    proj_id = proj["id"]

    pdf_data = make_sample_pdf([
        "Python is used in web development, automation, and data analysis.",
        "Architecture Flow:\nInput -> Processing -> Output"
    ])
    files = {"file": ("complete_guide.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "What is Python used for? Explain this diagram."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert "web development" in data["answer"].lower()
    assert "three-step process" in data["answer"].lower() or ("input" in data["answer"].lower() and "output" in data["answer"].lower())
    assert len(data["sources"]) >= 2
    assert any(s["page"] == 1 for s in data["sources"])
    assert any(s["page"] == 2 and s.get("visual_type") == "diagram" for s in data["sources"])

def test_ai_tutor_visual_cross_project_isolation(client, user_a_headers, user_b_headers):
    space_a = client.post("/spaces", headers=user_a_headers, json={"name": "User A Visuals"}).json()
    proj_a = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={"name": "Diagrams A"}).json()
    pdf_a = make_sample_pdf([
        "Confidential Diagram:\nSecretSensor -> QuantumKey -> VaultOutput"
    ])
    files_a = {"file": ("secret_diagram.pdf", io.BytesIO(pdf_a), "application/pdf")}
    client.post(f"/projects/{proj_a['id']}/materials", headers=user_a_headers, files=files_a)

    space_b = client.post("/spaces", headers=user_b_headers, json={"name": "User B Visuals"}).json()
    proj_b = client.post(f"/spaces/{space_b['id']}/projects", headers=user_b_headers, json={"name": "Project B"}).json()
    pdf_b = make_sample_pdf([
        "Public knowledge: Basic arithmetic and geometry."
    ])
    files_b = {"file": ("basic_math.pdf", io.BytesIO(pdf_b), "application/pdf")}
    client.post(f"/projects/{proj_b['id']}/materials", headers=user_b_headers, files=files_b)

    res = client.post(f"/projects/{proj_b['id']}/tutor/chat", headers=user_b_headers, json={
        "message": "Explain the SecretSensor diagram."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert len(data["sources"]) == 0
    assert "not contain enough information" in data["answer"].lower() or "couldn't find" in data["answer"].lower()

def test_ai_tutor_all_user_questions_suite(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "CS Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Python Notes"}).json()
    proj_id = proj["id"]

    pdf_pages = [
        "PYTHON BASICS Complete Beginner-Friendly Notes From 'What is Python?' to writing your first real programs",
        "Table of Contents\n1. What is Python?\n2. Variables and Data Types",
        "CHAPTER 1: What is Python?\nWhat is Python used for?\nDomain: Web Development (Django, Flask), Data Science & AI/ML (NumPy, Pandas, TensorFlow), Automation / Scripting, Scientific Computing, Game Development, Cybersecurity.",
        "CHAPTER 3: Variables and Data Types\nWhat is a Variable?\nA variable is a named container that stores a value in memory so you can use and reuse it later.\nCore Data Types:\nint: Whole numbers\nfloat: Decimal numbers\nstr: Text\nbool: Boolean True or False",
        "CHAPTER 8: Loops\nUnderstanding range(): range(1, 4) produces 1, 2, 3 because range(start, stop) starts at 1 and stops before 4, so the stop value 4 is not included.",
        "CHAPTER 9: Lists\nLists: Python list indexes start at 0. The first index of a Python list is 0.",
        "CHAPTER 10: Functions\nA function is a reusable, named block of code that performs a specific task. Functions let you avoid repeating code."
    ]
    pdf_data = make_sample_pdf(pdf_pages)
    files = {"file": ("Python_Complete_Notes.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    # Q1: What is Python used for?
    res1 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={"message": "What is Python used for?"}).json()
    assert res1["grounded"] is True
    assert not res1["answer"].lower().startswith("based on the course material")
    assert "web development" in res1["answer"].lower() or "automation" in res1["answer"].lower()
    assert "complete beginner-friendly notes" not in res1["answer"].lower()
    assert len(res1["sources"]) > 0

    # Q2: What is a variable?
    res2 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={"message": "What is a variable?"}).json()
    assert res2["grounded"] is True
    assert not res2["answer"].lower().startswith("based on the course material")
    assert "named container" in res2["answer"].lower() or "stores a value" in res2["answer"].lower()
    assert len(res2["sources"]) > 0

    # Q3: What is the first index of a Python list?
    res3 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={"message": "What is the first index of a Python list?"}).json()
    assert res3["grounded"] is True
    assert not res3["answer"].lower().startswith("based on the course material")
    assert "0" in res3["answer"]
    assert len(res3["sources"]) > 0

    # Q4: Why does range(1,4) produce 1, 2, 3?
    res4 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={"message": "Why does range(1,4) produce 1, 2, 3?"}).json()
    assert res4["grounded"] is True
    assert not res4["answer"].lower().startswith("based on the course material")
    assert "stop" in res4["answer"].lower() or "not included" in res4["answer"].lower() or "4" in res4["answer"]
    assert len(res4["sources"]) > 0

    # Q5: What is a function in Python?
    res5 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={"message": "What is a function in Python?"}).json()
    assert res5["grounded"] is True
    assert not res5["answer"].lower().startswith("based on the course material")
    assert "reusable" in res5["answer"].lower() or "block of code" in res5["answer"].lower() or "task" in res5["answer"].lower()
    assert len(res5["sources"]) > 0

    # Q6: What is the capital of France? (unsupported)
    res6 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={"message": "What is the capital of France?"}).json()
    assert res6["grounded"] is False
    assert len(res6["sources"]) == 0
    assert "not contain enough information" in res6["answer"].lower() or "couldn't find" in res6["answer"].lower()

    # Multi-part: What is a variable and what are four Python data types?
    res7 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={"message": "What is a variable and what are four Python data types?"}).json()
    assert res7["grounded"] is True
    assert not res7["answer"].lower().startswith("based on the course material")
    assert "named container" in res7["answer"].lower() or "variable" in res7["answer"].lower()
    assert "int" in res7["answer"].lower() and "float" in res7["answer"].lower()
    assert len(res7["sources"]) > 0

def test_ai_tutor_natural_phrasing_and_code_generation(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Code Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Code Proj"}).json()
    proj_id = proj["id"]

    pdf_pages = [
        "Python Basics: Python is an interpreted high-level general-purpose language used in web development and data science.",
        "Your First Program: To write a Hello World program in Python, use print(\"Hello, World!\"). Without quotes, Python thinks Hello is an undefined variable.",
        "Variables: A variable is a named container that stores a value in memory. Rules: start with a letter or underscore.",
        "Functions: A function is a reusable, named block of code. In Python, functions are defined using def greet(name): return f'Hello, {name}'."
    ]
    pdf_data = make_sample_pdf(pdf_pages)
    files = {"file": ("code_notes.pdf", io.BytesIO(pdf_data), "application/pdf")}
    client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)

    # 1. "Write a Python program for Hello World"
    res1 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "Write a Python program for Hello World"
    }).json()
    assert res1["grounded"] is True
    assert 'print("Hello, World!")' in res1["answer"]
    assert not res1["answer"].lower().startswith("based on the course material")
    assert len(res1["sources"]) > 0

    # 2. "How do I print Hello World in Python?"
    res2 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "How do I print Hello World in Python?"
    }).json()
    assert res2["grounded"] is True
    assert 'print("Hello, World!")' in res2["answer"]

    # 3. "Explain variables"
    res3 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "Explain variables"
    }).json()
    assert res3["grounded"] is True
    assert "named container" in res3["answer"].lower() or "stores a value" in res3["answer"].lower()

    # 4. "Give me an example of a Python function"
    res4 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "Give me an example of a Python function"
    }).json()
    assert res4["grounded"] is True
    assert "def " in res4["answer"]

    # 5. Multi-part: "What is Python and how do I print Hello World?"
    res5 = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={
        "message": "What is Python and how do I print Hello World?"
    }).json()
    assert res5["grounded"] is True
    assert "high-level" in res5["answer"].lower()
    assert 'print("Hello, World!")' in res5["answer"]
