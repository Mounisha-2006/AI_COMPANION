"""
Final End-to-End Verification Script: Complete Student Lifecycle & Material Testing (Day 3 — Prompt 3)
Verifies:
Part A:
  Register/Login -> Create Space -> Create Project -> Define learning goal ->
  Upload PDF -> Background processing -> Material Ready -> Ask Tutor ->
  Grounded Answer -> Citation -> Unsupported Question -> Appropriate Refusal ->
  Adaptive Quiz -> Performance -> Open-ended Assessment -> Mastery Update ->
  Growth Analysis -> Recommendation -> Project Analytics -> Global Analytics ->
  Continue Learning
Part B:
  Upload PDF -> Ready -> Delete PDF -> completely removed from retrieval ->
  Replace PDF -> old chunks/embeddings cannot be retrieved -> New PDF -> available to Tutor
"""
import io
import sys
import time
import uuid
from pathlib import Path
from fpdf import FPDF
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.database.session import SessionLocal
from app.models.document_chunk import DocumentChunk
from app.models.material import Material

def make_pdf(pages_text):
    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(w=0, h=10, text=text)
    return bytes(pdf.output())

def poll_material_ready(client, headers, project_id, material_id, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        res = client.get(f"/projects/{project_id}/materials/{material_id}", headers=headers)
        if res.status_code == 200:
            status = res.json().get("status", "").upper()
            if status == "READY":
                return res.json()
            elif status == "FAILED":
                raise RuntimeError(f"Material {material_id} processing failed: {res.json()}")
        time.sleep(0.5)
    raise TimeoutError(f"Material {material_id} did not become READY within {timeout}s")

def run_final_e2e_verification():
    print("================================================================")
    print("  DAY 3 — PROMPT 3: FINAL END-TO-END SYSTEM VERIFICATION")
    print("================================================================")

    client = TestClient(app)
    uid = uuid.uuid4().hex[:6]
    email = f"final_e2e_{uid}@example.com"
    password = "SecurePassword123!"

    # -------------------------------------------------------------
    # 1. Register & Login
    # -------------------------------------------------------------
    print("\n[Step 1] Registering and authenticating student...")
    reg_resp = client.post("/auth/register", json={
        "name": f"Student Final {uid}",
        "email": email,
        "password": password
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["email"] == email
    print(f"✓ Registered and verified user ID {user_data['id']} ({email}).")

    # -------------------------------------------------------------
    # 2. Create Space & Project with Learning Goal
    # -------------------------------------------------------------
    print("\n[Step 2] Creating Space and Project with learning goal...")
    space_resp = client.post("/spaces", headers=headers, json={
        "name": "Software Engineering Space",
        "description": "Domain for programming and computer systems."
    })
    assert space_resp.status_code == 201
    space_id = space_resp.json()["id"]

    proj_resp = client.post(f"/spaces/{space_id}/projects", headers=headers, json={
        "name": "Python Fundamentals",
        "description": "Comprehensive study of Python language constructs.",
        "learning_goal": "Master core syntax, data structures, and functions in Python"
    })
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    assert proj_resp.json()["learning_goal"] == "Master core syntax, data structures, and functions in Python"
    print(f"✓ Created Space ID {space_id} and Project ID {project_id} with explicit learning goal.")

    # -------------------------------------------------------------
    # 3. Upload PDF & Background Processing to READY
    # -------------------------------------------------------------
    print("\n[Step 3] Uploading Course Material PDF and polling for READY...")
    pdf_pages = [
        "Python Overview: Python is an interpreted, high-level, general-purpose programming language.\n"
        "Uses of Python: Python is used for web development, data science, automation, and scientific computing.",
        "Writing Your First Program: print('Hello, World!') outputs text to the console.\n"
        "Understanding Range: range(1, 4) produces 1, 2, 3. The stop value is always excluded.",
        "Common Data Types: int, float, str, and bool are fundamental Python data types.\n"
        "Lists: A list is an ordered, mutable collection defined with square brackets like fruits = ['apple', 'banana'].\n"
        "List indexing starts at 0 (zero-based indexing).",
        "Functions: A function is a reusable block of code defined using def greet(name): return f'Hello, {name}'."
    ]
    pdf_bytes = make_pdf(pdf_pages)
    upload_resp = client.post(
        f"/projects/{project_id}/materials",
        headers=headers,
        files={"file": ("python_core.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
    mat_id = upload_resp.json()["id"]

    mat_info = poll_material_ready(client, headers, project_id, mat_id)
    assert mat_info["status"].lower() == "ready"
    print(f"✓ Material ID {mat_id} successfully processed and is READY.")

    # -------------------------------------------------------------
    # 4. Ask Tutor: Grounded Answer & Citations
    # -------------------------------------------------------------
    print("\n[Step 4] Asking Tutor a grounded question ('What is Python?')...")
    tutor_q1 = client.post(f"/projects/{project_id}/tutor/chat", headers=headers, json={
        "message": "What is Python?"
    })
    assert tutor_q1.status_code == 200
    q1_data = tutor_q1.json()
    assert q1_data["grounded"] is True, f"Expected grounded=True: {q1_data}"
    assert len(q1_data["sources"]) > 0, "Expected non-empty sources"
    assert "interpreted" in q1_data["answer"].lower() or "high-level" in q1_data["answer"].lower()
    assert not q1_data["answer"].lower().startswith("based on the course material")
    print(f"✓ Tutor answered with grounded natural-language explanation and {len(q1_data['sources'])} citation(s).")

    # -------------------------------------------------------------
    # 5. Ask Tutor: Unsupported Question & Appropriate Refusal
    # -------------------------------------------------------------
    print("\n[Step 5] Asking Tutor an unsupported out-of-domain question...")
    unsupp_q = "What is the quantum mechanics equation for wave function collapse in this PDF?"
    tutor_q2 = client.post(f"/projects/{project_id}/tutor/chat", headers=headers, json={
        "message": unsupp_q
    })
    assert tutor_q2.status_code == 200
    q2_data = tutor_q2.json()
    assert q2_data["grounded"] is False, f"Expected grounded=False for unsupported question: {q2_data}"
    assert len(q2_data["sources"]) == 0, f"Expected zero sources for unsupported question: {q2_data}"
    assert any(p in q2_data["answer"].lower() for p in ["couldn't find", "not available", "does not contain"])
    print(f"✓ Tutor safely refused unsupported question without hallucinations: '{q2_data['answer'][:80]}...'")

    # -------------------------------------------------------------
    # 6. Adaptive Quiz Lifecycle
    # -------------------------------------------------------------
    print("\n[Step 6] Running Adaptive Knowledge Quiz...")
    quiz_start = client.post(f"/projects/{project_id}/quiz/start", headers=headers, json={"total_questions": 3})
    assert quiz_start.status_code == 201
    quiz_data = quiz_start.json()
    quiz_id = quiz_data["id"]
    curr_q = quiz_data.get("current_question")
    assert curr_q is not None, "Expected first adaptive quiz question"
    q_count = 0
    while curr_q:
        q_count += 1
        ans_text = curr_q.get("options", ["A"])[0] if curr_q.get("options") else "Sample Answer"
        ans_resp = client.post(
            f"/projects/{project_id}/quiz/{quiz_id}/answer",
            headers=headers,
            json={
                "question_id": curr_q["id"],
                "answer_text": ans_text
            }
        )
        assert ans_resp.status_code == 200
        ans_data = ans_resp.json()
        if ans_data.get("is_completed"):
            break
        curr_q = ans_data.get("next_question")

    # Get quiz performance
    quiz_final = client.get(f"/projects/{project_id}/quiz/{quiz_id}", headers=headers)
    assert quiz_final.status_code == 200
    final_score = quiz_final.json().get("score", 0)
    print(f"✓ Adaptive quiz completed. Score: {final_score} across {q_count} question(s).")

    # -------------------------------------------------------------
    # 7. Open-ended Assessment Flow
    # -------------------------------------------------------------
    print("\n[Step 7] Starting Open-ended Knowledge Assessment...")
    asmt_start = client.post(f"/projects/{project_id}/assessments/start", headers=headers, json={"total_questions": 2})
    assert asmt_start.status_code == 201
    asmt_data = asmt_start.json()
    asmt_id = asmt_data["id"]
    asmt_questions = asmt_data.get("questions", [])
    assert len(asmt_questions) > 0, "Expected assessment questions"

    # Submit answers for evaluation
    for aq in asmt_questions:
        sub_resp = client.post(
            f"/projects/{project_id}/assessments/{asmt_id}/submit",
            headers=headers,
            json={
                "question_id": aq["id"],
                "response_text": (
                    "Python is an interpreted, high-level programming language that provides clear syntax. "
                    "Functions are declared with def, and lists use 0-based indexing."
                )
            }
        )
        assert sub_resp.status_code == 200
        eval_data = sub_resp.json()
        assert "score" in eval_data
        assert "feedback" in eval_data

    asmt_final = client.get(f"/projects/{project_id}/assessments/{asmt_id}", headers=headers)
    assert asmt_final.status_code == 200
    overall_score = asmt_final.json().get("overall_score")
    print(f"✓ Open-ended assessment completed with rubric evaluation. Score: {overall_score}/100.")

    # -------------------------------------------------------------
    # 8. Concept Mastery Tracking
    # -------------------------------------------------------------
    print("\n[Step 8] Verifying Concept Mastery tracking...")
    mastery_resp = client.get(f"/projects/{project_id}/mastery", headers=headers)
    assert mastery_resp.status_code == 200
    mastery_list = mastery_resp.json()
    assert len(mastery_list) > 0, "Expected concept masteries recorded"
    print(f"✓ Concept mastery verified: {len(mastery_list)} concepts tracked.")

    # -------------------------------------------------------------
    # 9. Growth Analysis
    # -------------------------------------------------------------
    print("\n[Step 9] Verifying Learning Growth Analysis...")
    growth_resp = client.get(f"/projects/{project_id}/growth", headers=headers)
    assert growth_resp.status_code == 200
    growth_data = growth_resp.json()
    assert "overall_progress" in growth_data
    assert "concepts" in growth_data
    assert "summary" in growth_data
    assert len(growth_data["concepts"]) > 0
    first_concept = growth_data["concepts"][0]
    assert "status" in first_concept
    assert "change" in first_concept
    print(f"✓ Growth analysis verified: Progress={growth_data['overall_progress']}%, Tracked Concepts={len(growth_data['concepts'])}, First Status={first_concept['status']}.")

    # -------------------------------------------------------------
    # 10. Recommendations & Continue Learning
    # -------------------------------------------------------------
    print("\n[Step 10] Verifying Learning Recommendations & Continue Learning...")
    rec_resp = client.get(f"/projects/{project_id}/recommendations", headers=headers)
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    recs = rec_data.get("recommendations", [])
    assert len(recs) > 0, "Expected recommendations generated"
    rec_id = recs[0]["id"]

    # Mark recommendation completed (Continue Learning flow)
    done_resp = client.post(f"/projects/{project_id}/recommendations/{rec_id}/complete", headers=headers)
    assert done_resp.status_code == 200
    assert done_resp.json().get("recommendation", {}).get("completed_at") is not None
    print(f"✓ Recommendation completed successfully (ID: {rec_id}).")

    # -------------------------------------------------------------
    # 11. Project & Global Analytics
    # -------------------------------------------------------------
    print("\n[Step 11] Verifying Project and Global Analytics...")
    proj_analytics = client.get(f"/projects/{project_id}/analytics", headers=headers)
    assert proj_analytics.status_code == 200
    pa_data = proj_analytics.json()
    assert pa_data["project_id"] == project_id
    assert "activity" in pa_data
    assert "performance" in pa_data
    assert "recent_activities" in pa_data
    assert len(pa_data["recent_activities"]) > 0

    global_analytics = client.get("/analytics/global", headers=headers)
    assert global_analytics.status_code == 200
    ga_data = global_analytics.json()
    assert ga_data["total_spaces"] >= 1
    assert ga_data["total_projects"] >= 1
    assert "quiz_activity" in ga_data
    assert "projects_breakdown" in ga_data
    print("✓ Project Analytics and Global User Analytics aggregations verified.")

    # -------------------------------------------------------------
    # 12. Material Management: Upload Second PDF, Replace, and Delete (Part B)
    # -------------------------------------------------------------
    print("\n[Step 12] Verifying Material Testing (Upload -> Replace -> Invalidate -> Delete)...")
    
    # 12a. Upload second PDF: Classical Mechanics
    cm_pdf = make_pdf([
        "Classical mechanics describes the motion of macroscopic objects from projectiles to parts of machinery."
    ])
    upload_cm = client.post(
        f"/projects/{project_id}/materials",
        headers=headers,
        files={"file": ("classical_mechanics.pdf", io.BytesIO(cm_pdf), "application/pdf")}
    )
    assert upload_cm.status_code == 201
    cm_id = upload_cm.json()["id"]
    poll_material_ready(client, headers, project_id, cm_id)

    # Verify tutor can answer from classical mechanics
    cm_tutor = client.post(f"/projects/{project_id}/tutor/chat", headers=headers, json={
        "message": "What does classical mechanics describe?"
    })
    assert cm_tutor.status_code == 200
    assert cm_tutor.json()["grounded"] is True
    assert "macroscopic objects" in cm_tutor.json()["answer"].lower()
    print("✓ Second PDF uploaded and queryable by Tutor.")

    # 12b. Replace PDF with Thermodynamics
    thermo_pdf = make_pdf([
        "Thermodynamics describes heat, work, and temperature, and their relation to energy and entropy."
    ])
    replace_resp = client.put(
        f"/projects/{project_id}/materials/{cm_id}/replace",
        headers=headers,
        files={"file": ("thermodynamics.pdf", io.BytesIO(thermo_pdf), "application/pdf")}
    )
    assert replace_resp.status_code == 200
    poll_material_ready(client, headers, project_id, cm_id)

    # Verify old Classical Mechanics chunks are NO LONGER RETRIEVABLE
    db = SessionLocal()
    try:
        old_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.material_id == cm_id,
            DocumentChunk.chunk_text.ilike("%macroscopic objects%")
        ).all()
        assert len(old_chunks) == 0, "Stale classical mechanics chunks remained after replacement!"

        new_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.material_id == cm_id,
            DocumentChunk.chunk_text.ilike("%thermodynamics%")
        ).all()
        assert len(new_chunks) > 0, "New thermodynamics chunks were not ingested!"
    finally:
        db.close()

    # Query tutor with new thermodynamics material
    thermo_tutor = client.post(f"/projects/{project_id}/tutor/chat", headers=headers, json={
        "message": "What does thermodynamics describe?"
    })
    assert thermo_tutor.status_code == 200
    assert thermo_tutor.json()["grounded"] is True
    assert "heat" in thermo_tutor.json()["answer"].lower() or "temperature" in thermo_tutor.json()["answer"].lower()
    print("✓ Replace Material verified: old chunks invalidated, new chunks indexed and queryable.")

    # 12c. Delete Material
    del_resp = client.delete(f"/projects/{project_id}/materials/{cm_id}", headers=headers)
    assert del_resp.status_code in (200, 204)

    # Verify material and chunks are completely gone from DB
    db = SessionLocal()
    try:
        deleted_mat = db.query(Material).filter(Material.id == cm_id).first()
        assert deleted_mat is None, "Material record was not deleted from database!"
        remaining_chunks = db.query(DocumentChunk).filter(DocumentChunk.material_id == cm_id).all()
        assert len(remaining_chunks) == 0, "Document chunks remained after material deletion!"
    finally:
        db.close()
    print("✓ Delete Material verified: material and all chunks completely removed from retrieval.")

    print("\n================================================================")
    print("  ALL END-TO-END VERIFICATION STEPS PASSED SUCCESSFULLY! (100%)")
    print("================================================================")

if __name__ == "__main__":
    run_final_e2e_verification()
