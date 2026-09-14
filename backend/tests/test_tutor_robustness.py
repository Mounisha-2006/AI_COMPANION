import io
import pytest
from fpdf import FPDF
from app.services.ai_service import AIService

def make_sample_pdf(pages_text):
    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(w=0, h=10, text=text)
    return bytes(pdf.output())

def test_tutor_16_question_scenarios(client, user_a_headers):
    """
    Comprehensive verification of all 16 required question scenarios:
    1. Python overview: 'What is Python?'
    2. Simple explanation: 'Explain Python in simple words.'
    3. Uses: 'Tell me what Python is used for.'
    4. Hello World program: 'Can you write a Python Hello World program?'
    5. Print Hello World: 'How do I print Hello World in Python?'
    6. Function explanation with code: 'What is a function in Python?'
    7. List indexing: 'Explain list indexing.'
    8. First index: 'What is the first index of a list in Python?'
    9. Range: 'What does range(1, 4) produce and why?'
    10. Diagram: 'Explain the diagram on Page 2.'
    11. Table: 'Explain the table on Page 3.'
    12. Image / Figure: 'What information is shown in the image on Page 4?'
    13. Compound multi-question: 'What is Python, what are its uses, and what are four Python data types?'
    14. Follow-up 1: 'What is a Python list?' followed by 'Give me an example.'
    15. Follow-up 2: 'What is a function in Python?' followed by 'How do I call it?'
    16. Unsupported question: 'What is the quantum mechanics equation for wave function collapse in this PDF?'
    """
    # 1. Create space and project
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Computer Science Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={
        "name": "Python Mastery",
        "learning_goal": "Master Python programming fundamentals"
    }).json()
    proj_id = proj["id"]

    # 2. Upload course material with text, tables, and diagrams
    pages = [
        # Page 1: Overview & Uses
        "Python Overview: Python is an interpreted high-level general-purpose language known for simplicity and readability.\n"
        "Uses of Python: Python is used for web development, data science, machine learning, and automation scripting.",
        
        # Page 2: Diagram & Syntax
        "Pipeline Architecture:\n"
        "Input -> Processing -> Output\n"
        "Writing Your First Program:\n"
        "print(\"Hello, World!\") displays text to the screen.\n"
        "Understanding Range: range(1, 4) generates 1, 2, 3. The stop value 4 is excluded.",
        
        # Page 3: Tables & Data Types
        "| Data Type | Description |\n"
        "| int | whole numbers without decimals |\n"
        "| float | floating point decimal numbers |\n"
        "| str | textual character strings |\n"
        "| bool | boolean True or False |\n"
        "Common Data Types: int, float, str, and bool are core Python types.",
        
        # Page 4: Functions & Lists
        "Figure 4: Computational memory stack displaying function call execution.\n"
        "Functions: A function is a reusable, named block of code defined using def greet(name): return f'Hello, {name}'.\n"
        "List Indexing: In Python lists, indexes start at 0 (zero-based indexing). fruits = ['apple', 'banana', 'cherry'], fruits[0] gives apple."
    ]
    pdf_bytes = make_sample_pdf(pages)
    files = {"file": ("python_comprehensive.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)
    assert upload_res.status_code == 201

    def ask(question: str):
        res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_a_headers, json={"message": question})
        assert res.status_code == 200
        return res.json()

    # Q1: Python Overview
    r1 = ask("What is Python?")
    assert r1["grounded"] is True
    assert "interpreted" in r1["answer"].lower() or "high-level" in r1["answer"].lower()
    assert not r1["answer"].strip().endswith("?")
    assert not r1["answer"].lower().startswith("based on the course material")
    assert len(r1["sources"]) > 0

    # Q2: Simple words explanation
    r2 = ask("Explain Python in simple words.")
    assert r2["grounded"] is True
    assert "readability" in r2["answer"].lower() or "high-level" in r2["answer"].lower() or "simple" in r2["answer"].lower()

    # Q3: Uses of Python
    r3 = ask("Tell me what Python is used for.")
    assert r3["grounded"] is True
    assert "web development" in r3["answer"].lower() or "data science" in r3["answer"].lower() or "automation" in r3["answer"].lower()
    assert len(r3["sources"]) > 0

    # Q4: Hello World program
    r4 = ask("Can you write a Python Hello World program?")
    assert r4["grounded"] is True
    assert 'print("Hello, World!")' in r4["answer"] or "print('Hello, World!')" in r4["answer"]

    # Q5: Print Hello World variant
    r5 = ask("How do I print Hello World in Python?")
    assert r5["grounded"] is True
    assert 'print("Hello, World!")' in r5["answer"] or "print('Hello, World!')" in r5["answer"]

    # Q6: Function explanation with code
    r6 = ask("What is a function in Python?")
    assert r6["grounded"] is True
    assert "reusable" in r6["answer"].lower() or "block of code" in r6["answer"].lower()
    assert "def " in r6["answer"]

    # Q7: List indexing
    r7 = ask("Explain list indexing.")
    assert r7["grounded"] is True
    assert "0" in r7["answer"]
    assert "zero-based" in r7["answer"].lower() or "index" in r7["answer"].lower()

    # Q8: First index of a list
    r8 = ask("What is the first index of a list in Python?")
    assert r8["grounded"] is True
    assert "0" in r8["answer"]
    assert "zero-based" in r8["answer"].lower()

    # Q9: Range mechanics
    r9 = ask("What does range(1, 4) produce and why?")
    assert r9["grounded"] is True
    assert "1, 2, 3" in r9["answer"] or "1,2,3" in r9["answer"]
    assert "excluded" in r9["answer"].lower() or "stop" in r9["answer"].lower() or "not included" in r9["answer"].lower()

    # Q10: Diagram explanation
    r10 = ask("Explain the diagram on Page 2.")
    assert r10["grounded"] is True
    assert "input" in r10["answer"].lower() and "output" in r10["answer"].lower()

    # Q11: Table explanation
    r11 = ask("Explain the table on Page 3.")
    assert r11["grounded"] is True
    assert "table" in r11["answer"].lower() or "data type" in r11["answer"].lower() or "int" in r11["answer"].lower()

    # Q12: Image / Figure explanation
    r12 = ask("What information is shown in the image on Page 4?")
    assert r12["grounded"] is True
    assert "page 4" in r12["answer"].lower() or "figure" in r12["answer"].lower() or "memory" in r12["answer"].lower() or len(r12["sources"]) > 0

    # Q13: Compound multi-question
    r13 = ask("What is Python, what are its uses, and what are four Python data types?")
    assert r13["grounded"] is True
    # Should answer all three parts
    ans13_low = r13["answer"].lower()
    assert "interpreted" in ans13_low or "programming language" in ans13_low
    assert "web development" in ans13_low or "data science" in ans13_low or "automation" in ans13_low
    assert "int" in ans13_low and "float" in ans13_low
    assert len(r13["sources"]) >= 1

    # Q14: Follow-up 1 (List followed by 'Give me an example.')
    r14_init = ask("What is a Python list?")
    assert r14_init["grounded"] is True
    r14_follow = ask("Give me an example.")
    assert r14_follow["grounded"] is True
    assert "[" in r14_follow["answer"] and "]" in r14_follow["answer"]
    assert "fruits" in r14_follow["answer"].lower() or "list" in r14_follow["answer"].lower() or "languages" in r14_follow["answer"].lower()

    # Q15: Follow-up 2 (Function followed by 'How do I call it?')
    r15_init = ask("What is a function?")
    assert r15_init["grounded"] is True
    r15_follow = ask("How do I call it?")
    assert r15_follow["grounded"] is True
    assert "(" in r15_follow["answer"] and ")" in r15_follow["answer"]
    assert "parentheses" in r15_follow["answer"].lower() or "call" in r15_follow["answer"].lower() or "greet" in r15_follow["answer"].lower()

    # Q16: Unsupported question rejection
    r16 = ask("What is the quantum mechanics equation for wave function collapse in this PDF?")
    assert r16["grounded"] is False
    assert len(r16["sources"]) == 0
    assert "couldn't find" in r16["answer"].lower() or "not available" in r16["answer"].lower()
