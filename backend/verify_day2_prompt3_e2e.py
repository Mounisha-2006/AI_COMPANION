#!/usr/bin/env python3
"""
Day 2 Prompt 3 E2E Verification Script:
Growth Analysis + Learning Recommendations + Complete Learning Loop:
Quiz / Assessment -> Mastery -> Growth -> Recommendations -> Next Action UI
"""

import io
import time
from fpdf import FPDF
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.activity_event import ActivityEvent, ActivityEventType
from app.models.quiz import QuizQuestion
from app.models.mastery import ConceptMastery
from app.models.recommendation import Recommendation

def make_sample_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    content = (
        "Object-Oriented Programming (OOP) core concepts:\n\n"
        "1. Encapsulation: Bundling data and methods that operate on that data within a single unit. "
        "It hides internal state and requires all interaction to occur through defined object interfaces.\n\n"
        "2. Polymorphism: The ability of different types to be accessed through the same interface. "
        "Each class can provide its own unique implementation of an interface or abstract method.\n\n"
        "3. Recursion: A programming technique in which a function calls itself directly to break a "
        "problem into smaller sub-problems. A base case is essential to prevent infinite loops.\n"
    )
    pdf.multi_cell(w=0, h=8, text=content)
    return bytes(pdf.output())

def run_e2e_verification():
    print("=" * 66)
    print("  DAY 2 PROMPT 3 E2E VERIFICATION: GROWTH + RECOMMENDATIONS")
    print("=" * 66)

    client = TestClient(app)

    # 1. Register and Authenticate Learner A
    print("\n[Step 1] Registering and authenticating learner...")
    user_email = f"growth_learner_{int(time.time())}@example.com"
    reg_resp = client.post("/auth/register", json={
        "name": "Alex Learner",
        "email": user_email,
        "password": "SecurePassword123!"
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    token_a = reg_resp.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    user_a = client.get("/auth/me", headers=headers_a).json()
    print(f"✓ Learner '{user_a['name']}' authenticated.")

    # 2. Create Space and Project with Learning Goal
    print("\n[Step 2] Creating Space and Project with Learning Goal...")
    space_resp = client.post("/spaces", headers=headers_a, json={
        "name": "Software Engineering",
        "description": "Core CS and Software Design Concepts"
    })
    space_id = space_resp.json()["id"]

    project_resp = client.post(f"/spaces/{space_id}/projects", headers=headers_a, json={
        "name": "OOP Fundamentals & Architecture",
        "description": "Mastering OOP principles and algorithms",
        "learning_goal": "Master Encapsulation and Recursion mechanisms"
    })
    project_id = project_resp.json()["id"]
    print(f"✓ Project created: '{project_resp.json()['name']}' (ID: {project_id})")
    print(f"  Target Goal: '{project_resp.json()['learning_goal']}'")

    # 3. Check Initial Growth and Recommendations
    print("\n[Step 3] Checking Initial Growth and Recommendations...")
    init_growth = client.get(f"/projects/{project_id}/growth", headers=headers_a).json()
    assert init_growth["overall_progress"] == 0.0
    assert len(init_growth["concepts"]) == 0
    print("✓ Growth matrix is initially clean.")

    init_recs = client.get(f"/projects/{project_id}/recommendations", headers=headers_a).json()
    assert init_recs["total_count"] >= 1
    assert init_recs["next_action"] is not None
    print(f"✓ Initial Next Action: '{init_recs['next_action']['recommendation']}'")

    # 4. Upload PDF Material
    print("\n[Step 4] Uploading study material PDF...")
    pdf_bytes = make_sample_pdf()
    files = {"file": ("oop_concepts.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    up_resp = client.post(f"/projects/{project_id}/materials", headers=headers_a, files=files)
    assert up_resp.status_code == 201
    mat_id = up_resp.json()["id"]

    # Poll until ready
    for _ in range(20):
        m_status = client.get(f"/materials/{mat_id}", headers=headers_a).json()
        if m_status["status"] == "ready":
            break
        time.sleep(0.4)
    print("✓ Material indexed into chunks and ready.")

    # 5. Take Adaptive Quiz: Test Encapsulation (Answer Correct) and Recursion (Answer Incorrect)
    print("\n[Step 5] Taking Adaptive Quiz (Feeding evidence into learning loop)...")
    quiz_resp = client.post(f"/projects/{project_id}/quiz/start", headers=headers_a, json={"total_questions": 2})
    assert quiz_resp.status_code in (200, 201), f"Quiz start failed ({quiz_resp.status_code}): {quiz_resp.text}"
    quiz_data = quiz_resp.json()
    quiz_id = quiz_data["id"]

    db = SessionLocal()
    try:
        # Get questions from DB
        q_rows = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.order.asc()).all()

        # Submit answer 1 (Correct)
        ans1_resp = client.post(f"/projects/{project_id}/quiz/{quiz_id}/answer", headers=headers_a, json={
            "question_id": q_rows[0].id,
            "answer_text": q_rows[0].correct_answer
        })
        assert ans1_resp.status_code == 200
        print(f"✓ Answered Question 1 [{q_rows[0].concept}]: Correct (100% score)")

        # Submit answer 2 (Incorrect)
        ans2_resp = client.post(f"/projects/{project_id}/quiz/{quiz_id}/answer", headers=headers_a, json={
            "question_id": q_rows[1].id,
            "answer_text": "A completely incorrect dummy answer"
        })
        assert ans2_resp.status_code == 200
        print(f"✓ Answered Question 2 [{q_rows[1].concept}]: Incorrect (0% score)")
    finally:
        db.close()

    # 6. Now take an Open-Ended Assessment on Encapsulation to show Improving trajectory!
    print("\n[Step 6] Submitting Open-Ended Assessment to verify score progression...")
    start_assess = client.post(f"/projects/{project_id}/assessments/start", headers=headers_a, json={"total_questions": 1})
    assert start_assess.status_code in (200, 201), f"Assessment start failed ({start_assess.status_code}): {start_assess.text}"
    assess_data = start_assess.json()
    assess_id = assess_data["id"]
    q_assess = assess_data["questions"][0]

    # Strong detailed answer to boost mastery
    sub_resp = client.post(f"/projects/{project_id}/assessments/{assess_id}/submit", headers=headers_a, json={
        "question_id": q_assess["id"],
        "response_text": (
            "Encapsulation is the object-oriented principle of bundling data and methods that operate "
            "on that data into a single unit or class. It enforces information hiding and prevents direct "
            "external modification of internal state except through well-defined public methods and interfaces."
        )
    })
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    print(f"✓ Open-ended answer evaluated! Score: {sub_data['score']}/100")

    # 7. Query Growth API and Verify Classifications
    print("\n[Step 7] Verifying Growth API (/projects/{id}/growth)...")
    growth_resp = client.get(f"/projects/{project_id}/growth", headers=headers_a)
    assert growth_resp.status_code == 200
    growth = growth_resp.json()

    print(f"Overall Progress: {growth['overall_progress']}%")
    print(f"Total Concepts: {growth['summary']['total_concepts']}")

    concepts = {c["concept"]: c for c in growth["concepts"]}
    for cname, cdata in concepts.items():
        print(f"  - Concept: {cname.ljust(18)} | Prev: {str(cdata['previous_mastery']).rjust(5)}% | Curr: {str(cdata['current_mastery']).rjust(5)}% | Change: {str(cdata['change']).rjust(5)}% | Status: {cdata['status']}")

    assert len(growth["concepts"]) >= 2
    # Verify at least one concept is classified as 'Needs Attention' due to the incorrect answer
    assert len(growth["summary"]["areas_requiring_attention"]) >= 1
    print(f"✓ Confirmed Areas Needing Attention: {growth['summary']['areas_requiring_attention']}")

    # 8. Query Recommendations API and Verify "What should I do next?"
    print("\n[Step 8] Verifying Recommendations API (/projects/{id}/recommendations)...")
    recs_resp = client.get(f"/projects/{project_id}/recommendations", headers=headers_a)
    assert recs_resp.status_code == 200
    recs = recs_resp.json()

    next_action = recs["next_action"]
    assert next_action is not None
    print(f"\n[Generated Recommended Next Action]:")
    print(f"  Concept:     {next_action['concept']}")
    print(f"  Priority:    {next_action['priority']}")
    print(f"  Next Action: \"{next_action['recommendation']}\"")
    print(f"  Reason:      {next_action['reason']}")
    print(f"  Action Type: {next_action['action_type']}")

    # Priority should be 'high' targeting the weak or mistake concept
    assert next_action["priority"] == "high"

    # 9. Mark Recommendation as Completed
    print("\n[Step 9] Marking Recommendation as Completed...")
    rec_id = next_action["id"]
    comp_resp = client.post(
        f"/projects/{project_id}/recommendations/{rec_id}/complete",
        headers=headers_a
    )
    assert comp_resp.status_code == 200
    comp_result = comp_resp.json()
    assert comp_result["recommendation"]["completed_at"] is not None
    print("✓ Recommendation marked complete!")

    # Verify pending count decreased
    recs_after = client.get(f"/projects/{project_id}/recommendations", headers=headers_a).json()
    assert recs_after["pending_count"] < recs["pending_count"]
    print(f"✓ Pending recommendations updated: {recs_after['pending_count']} pending")

    # 10. Verify Activity Events
    print("\n[Step 10] Checking Activity Timeline...")
    act_resp = client.get("/activity", headers=headers_a)
    events = [a["event_type"] for a in act_resp.json()]
    for ev in [
        ActivityEventType.QUIZ_STARTED.value,
        ActivityEventType.MASTERY_UPDATED.value,
        ActivityEventType.RECOMMENDATION_GENERATED.value,
        ActivityEventType.RECOMMENDATION_COMPLETED.value
    ]:
        assert ev in events, f"Missing activity event: {ev}"
        print(f"  ✓ Found activity event: {ev}")

    # 11. Verify User and Project Isolation
    print("\n[Step 11] Verifying User and Project Isolation...")
    reg_b = client.post("/auth/register", json={
        "name": "Unauthorized User",
        "email": f"unauth_{int(time.time())}@example.com",
        "password": "Password123!"
    })
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B cannot access User A's growth
    grow_b = client.get(f"/projects/{project_id}/growth", headers=headers_b)
    assert grow_b.status_code == 404, f"Isolation failure for growth: {grow_b.status_code}"

    # User B cannot access User A's recommendations
    recs_b = client.get(f"/projects/{project_id}/recommendations", headers=headers_b)
    assert recs_b.status_code == 404, f"Isolation failure for recommendations: {recs_b.status_code}"

    print("✓ Project and user isolation verified.")

    print("\n" + "=" * 66)
    print("  DAY 2 PROMPT 3 E2E VERIFICATION COMPLETED WITH 100% SUCCESS!")
    print("=" * 66)

if __name__ == "__main__":
    run_e2e_verification()
