"""
End-to-End Verification Script for Day 2 Prompt 2:
Open-Ended Assessment & Concept Mastery
"""
import io
import time
import uuid
from fpdf import FPDF
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.activity_event import ActivityEvent, ActivityEventType
from app.models.assessment import Assessment, AssessmentResponse
from app.models.mastery import ConceptMastery

def make_pdf(pages_text):
    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(w=0, h=10, text=text)
    return bytes(pdf.output())

def run_e2e_prompt2():
    print("================================================================")
    print("  DAY 2 PROMPT 2 E2E VERIFICATION: ASSESSMENT + CONCEPT MASTERY")
    print("================================================================")

    client = TestClient(app)
    uid = uuid.uuid4().hex[:6]
    email = f"learner_{uid}@example.com"
    password = "SecurePassword123!"

    # 1. Register & Authenticate User
    print("\n[Step 1] Registering and authenticating learner...")
    reg_res = client.post("/auth/register", json={"name": "Morgan Learner", "email": email, "password": password})
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Learner authenticated.")

    # 2. Create Space and Project
    print("\n[Step 2] Creating Space and Project...")
    sp_res = client.post("/spaces", headers=headers, json={"name": "Software Engineering"}).json()
    pr_res = client.post(f"/spaces/{sp_res['id']}/projects", headers=headers, json={
        "name": "Design Patterns & Modularity",
        "description": "Object-oriented design principles and patterns.",
        "learning_goal": "Understand encapsulation, polymorphism, and dependency injection."
    }).json()
    proj_id = pr_res["id"]
    print(f"✓ Project created: '{pr_res['name']}' (ID: {proj_id})")

    # 3. Verify Empty Concept Mastery
    print("\n[Step 3] Checking Initial Concept Mastery...")
    m_init = client.get(f"/projects/{proj_id}/mastery", headers=headers).json()
    assert len(m_init["concepts"]) == 0
    assert len(m_init["areas_needing_attention"]) == 0
    print("✓ Initial mastery confirmed empty.")

    # 4. Upload Material
    print("\n[Step 4] Uploading PDF study materials...")
    pdf_content = make_pdf([
        "Encapsulation is the bundling of data and the methods that operate on that data within a single unit or class, restricting direct access to internal state.",
        "Polymorphism allows objects of different classes to be treated as objects of a common superclass, enabling flexible and interchangeable code design.",
        "Dependency Injection is a design pattern where an object receives its dependencies from an external source rather than creating them internally."
    ])
    files = {"file": ("patterns_chapter.pdf", io.BytesIO(pdf_content), "application/pdf")}
    up_res = client.post(f"/projects/{proj_id}/materials", headers=headers, files=files)
    assert up_res.status_code == 201
    mat_id = up_res.json()["id"]

    for _ in range(25):
        poll = client.get(f"/materials/{mat_id}", headers=headers).json()
        if poll["status"] == "ready":
            break
        time.sleep(0.4)
    assert poll["status"] == "ready"
    print("✓ Material successfully indexed into chunks.")

    # 5. Start Open-Ended Assessment
    print("\n[Step 5] Starting Open-Ended Assessment with 2 questions...")
    start_res = client.post(f"/projects/{proj_id}/assessments/start", headers=headers, json={"total_questions": 2})
    assert start_res.status_code == 201
    assessment = start_res.json()
    assess_id = assessment["id"]
    assert assessment["status"] == "in_progress"
    assert len(assessment["questions"]) == 2
    q1 = assessment["questions"][0]
    q2 = assessment["questions"][1]
    print(f"✓ Assessment #{assess_id} started.")
    print(f"  Question 1 [{q1['concept']}]: {q1['question_text']}")
    print(f"  Question 2 [{q2['concept']}]: {q2['question_text']}")

    # 6. Submit Thoughtful Response for Question 1
    print("\n[Step 6] Submitting learner's response for Question 1 in own words...")
    good_answer = (
        f"{q1['concept']} is a fundamental object-oriented programming principle that bundles data and methods "
        "together inside a class, protecting internal states by restricting direct access from outside components."
    )
    sub1_res = client.post(f"/projects/{proj_id}/assessments/{assess_id}/submit", headers=headers, json={
        "question_id": q1["id"],
        "response_text": good_answer
    })
    assert sub1_res.status_code == 200
    eval1 = sub1_res.json()

    print("\n[Structured AI Evaluation Received for Question 1]:")
    print(f"  Score: {eval1['score']} / 100")
    print(f"  Understanding: {eval1['understanding']}")
    print(f"  Accuracy: {eval1['accuracy']}")
    print(f"  Strengths: {eval1['strengths']}")
    print(f"  Missing Concepts: {eval1['missing_concepts']}")
    print(f"  Feedback: {eval1['feedback']}")

    assert eval1["score"] >= 70
    assert len(eval1["strengths"]) > 0
    assert len(eval1["feedback"]) > 0

    # 7. Check Concept Mastery Update After Question 1
    print("\n[Step 7] Verifying Concept Mastery updated from Assessment 1...")
    m_after_q1 = client.get(f"/projects/{proj_id}/mastery", headers=headers).json()
    assert len(m_after_q1["concepts"]) >= 1
    mastery_c1 = next(c for c in m_after_q1["concepts"] if c["concept"] == q1["concept"].capitalize())
    print(f"✓ Mastery for '{mastery_c1['concept']}': {mastery_c1['mastery_score']}% (confidence: {mastery_c1['confidence']}, evidence count: {mastery_c1['evidence_count']})")
    assert mastery_c1["mastery_score"] >= 70

    # 8. Submit Incomplete Response for Question 2 to Test Missing Concepts & Areas Needing Attention
    print("\n[Step 8] Submitting incomplete response for Question 2...")
    brief_answer = "It is used in coding."
    sub2_res = client.post(f"/projects/{proj_id}/assessments/{assess_id}/submit", headers=headers, json={
        "question_id": q2["id"],
        "response_text": brief_answer
    })
    assert sub2_res.status_code == 200
    eval2 = sub2_res.json()

    print("\n[Structured AI Evaluation Received for Question 2]:")
    print(f"  Score: {eval2['score']} / 100")
    print(f"  Understanding: {eval2['understanding']}")
    print(f"  Missing Concepts: {eval2['missing_concepts']}")
    print(f"  Feedback: {eval2['feedback']}")

    assert eval2["score"] < 60
    assert len(eval2["missing_concepts"]) > 0

    # 9. Verify Assessment Status Completed and Overall Score
    print("\n[Step 9] Checking completed Assessment details...")
    assess_detail = client.get(f"/projects/{proj_id}/assessments/{assess_id}", headers=headers).json()
    assert assess_detail["status"] == "completed"
    assert assess_detail["overall_score"] is not None
    print(f"✓ Assessment completed! Overall score: {assess_detail['overall_score']}%")

    # 10. Check Concept Mastery with "Areas Needing Attention"
    print("\n[Step 10] Checking Concept Mastery dashboard...")
    m_final = client.get(f"/projects/{proj_id}/mastery", headers=headers).json()
    print("Concept Mastery Breakdown:")
    for item in m_final["concepts"]:
        bars = "█" * int(item["mastery_score"] // 10) + "░" * (10 - int(item["mastery_score"] // 10))
        print(f"  - {item['concept']:<20} {bars} {item['mastery_score']}% (conf: {item['confidence']}, evidence: {item['evidence_count']})")

    print(f"Areas Needing Attention: {m_final['areas_needing_attention']}")
    assert q2["concept"].capitalize() in m_final["areas_needing_attention"]

    # 11. Verify Activity Events
    print("\n[Step 11] Checking Activity Timeline events...")
    act_res = client.get("/activity?limit=30", headers=headers).json()
    event_types = [a["event_type"] for a in act_res]
    expected_events = [
        "ASSESSMENT_STARTED",
        "ASSESSMENT_SUBMITTED",
        "ASSESSMENT_EVALUATED",
        "MASTERY_UPDATED"
    ]
    for ev in expected_events:
        assert ev in event_types, f"Missing activity event: {ev}"
        print(f"  ✓ Found activity event: {ev}")

    # 12. Verify Project Isolation
    print("\n[Step 12] Verifying Project and User Isolation...")
    reg_b = client.post("/auth/register", json={"name": "User B", "email": f"b_{uid}@example.com", "password": "PasswordB123!"}).json()
    headers_b = {"Authorization": f"Bearer {reg_b['access_token']}"}

    assert client.get(f"/projects/{proj_id}/assessments/{assess_id}", headers=headers_b).status_code == 404
    assert client.get(f"/projects/{proj_id}/assessments", headers=headers_b).status_code == 404
    assert client.get(f"/projects/{proj_id}/mastery", headers=headers_b).status_code == 404
    print("✓ Project and user isolation verified.")

    print("\n================================================================")
    print("  DAY 2 PROMPT 2 E2E VERIFICATION COMPLETED WITH 100% SUCCESS!  ")
    print("================================================================")

if __name__ == "__main__":
    run_e2e_prompt2()
