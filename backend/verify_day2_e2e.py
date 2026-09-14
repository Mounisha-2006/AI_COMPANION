"""
End-to-End Verification Script for Day 2: Material Management & Adaptive Quiz
"""
import io
import time
import uuid
from fpdf import FPDF
from fastapi.testclient import TestClient
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

def run_day2_e2e_verification():
    print("==================================================")
    print("  DAY 2 END-TO-END VERIFICATION: AI STUDY COMPANION")
    print("==================================================")

    client = TestClient(app)
    uid = uuid.uuid4().hex[:6]
    email = f"student_day2_{uid}@example.com"
    password = "StrongPassword123!"

    # 1. Register & Login
    print("\n[Step 1] Registering and authenticating user...")
    reg_resp = client.post("/auth/register", json={"name": "Alice Day2", "email": email, "password": password})
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Registered and obtained JWT bearer token.")

    # 2. Create Space and Project
    print("\n[Step 2] Creating Space and Project...")
    sp_resp = client.post("/spaces", headers=headers, json={"name": "Computer Science"})
    assert sp_resp.status_code == 201
    space_id = sp_resp.json()["id"]

    pr_resp = client.post(f"/spaces/{space_id}/projects", headers=headers, json={
        "name": "Algorithms Project",
        "description": "Study of classical sorting and search algorithms.",
        "learning_goal": "Master Divide and Conquer and Dynamic Programming"
    })
    assert pr_resp.status_code == 201
    project_id = pr_resp.json()["id"]
    print(f"✓ Created Project ID {project_id} in Space ID {space_id}.")

    # 3. Upload Material A
    print("\n[Step 3] Uploading Initial PDF (QuickSort & Binary Search)...")
    pdf_a_bytes = make_pdf([
        "QuickSort is an efficient sorting algorithm using a divide-and-conquer strategy with an average time complexity of O(n log n).",
        "Binary Search requires a sorted array and operates in logarithmic time O(log n) by repeatedly halving the search interval.",
        "Dynamic Programming solves optimization problems by breaking them into overlapping subproblems and memoizing results."
    ])
    files_a = {"file": ("algorithms_v1.pdf", io.BytesIO(pdf_a_bytes), "application/pdf")}
    up_resp = client.post(f"/projects/{project_id}/materials", headers=headers, files=files_a)
    assert up_resp.status_code == 201
    mat_id = up_resp.json()["id"]

    # Poll until ready
    print("Waiting for background indexing...")
    for _ in range(25):
        poll = client.get(f"/materials/{mat_id}", headers=headers).json()
        if poll["status"] == "ready":
            break
        time.sleep(0.4)
    assert poll["status"] == "ready", f"Material processing failed: {poll}"
    print("✓ Material indexed and ready.")

    # 4. Start Adaptive Quiz
    print("\n[Step 4] Starting Adaptive Quiz with 3 questions...")
    quiz_start = client.post(f"/projects/{project_id}/quiz/start", headers=headers, json={"total_questions": 3})
    assert quiz_start.status_code == 201
    quiz = quiz_start.json()
    quiz_id = quiz["id"]
    assert quiz["status"] == "in_progress"
    assert quiz["total_questions"] == 3
    q1 = quiz["current_question"]
    assert q1 is not None
    assert "correct_answer" not in q1, "Security check: correct_answer must not leak to client!"
    print(f"✓ Quiz #{quiz_id} started. Question 1: '{q1['question_text']}' [Concept: {q1['concept']}, Difficulty: {q1['difficulty']}]")

    # 5. Answer Question 1 Incorrectly
    print("\n[Step 5] Submitting deliberate incorrect answer for Question 1...")
    ans1_resp = client.post(f"/projects/{project_id}/quiz/{quiz_id}/answer", headers=headers, json={
        "question_id": q1["id"],
        "answer_text": "Intentionally Incorrect Answer Option"
    })
    assert ans1_resp.status_code == 200
    ans1 = ans1_resp.json()
    assert ans1["is_correct"] is False
    assert ans1["current_score"] == 0
    assert "Incorrect" in ans1["feedback"]
    assert ans1["is_completed"] is False
    q2 = ans1["next_question"]
    print(f"✓ Feedback received: {ans1['feedback']}")
    print(f"✓ Next adaptive question chosen: '{q2['question_text']}' [Concept: {q2['concept']}, Difficulty: {q2['difficulty']}]")

    # 6. Answer Question 2 Correctly
    print("\n[Step 6] Submitting correct answer for Question 2...")
    db = SessionLocal()
    from app.models.quiz import QuizQuestion
    db_q2 = db.query(QuizQuestion).filter(QuizQuestion.id == q2["id"]).first()
    correct_ans_2 = db_q2.correct_answer

    ans2_resp = client.post(f"/projects/{project_id}/quiz/{quiz_id}/answer", headers=headers, json={
        "question_id": q2["id"],
        "answer_text": correct_ans_2
    })
    assert ans2_resp.status_code == 200
    ans2 = ans2_resp.json()
    assert ans2["is_correct"] is True
    assert ans2["current_score"] == 1
    q3 = ans2["next_question"]
    print(f"✓ Feedback received: {ans2['feedback']}")

    # 7. Answer Question 3 Correctly (Final Question)
    print("\n[Step 7] Submitting correct answer for final Question 3...")
    db_q3 = db.query(QuizQuestion).filter(QuizQuestion.id == q3["id"]).first()
    correct_ans_3 = db_q3.correct_answer
    db.close()

    ans3_resp = client.post(f"/projects/{project_id}/quiz/{quiz_id}/answer", headers=headers, json={
        "question_id": q3["id"],
        "answer_text": correct_ans_3
    })
    assert ans3_resp.status_code == 200
    ans3 = ans3_resp.json()
    assert ans3["is_correct"] is True
    assert ans3["current_score"] == 2
    assert ans3["is_completed"] is True
    assert ans3["summary"] is not None
    summary = ans3["summary"]
    print(f"✓ Quiz completed! Final score: {summary['score']} / {summary['total_questions']} ({summary['percentage']}%)")
    print(f"✓ Weak concepts identified needing attention: {summary['weak_concepts']}")
    assert q1["concept"] in summary["weak_concepts"]

    # 8. List Quizzes
    print("\n[Step 8] Listing previous project quizzes...")
    quizzes_resp = client.get(f"/projects/{project_id}/quiz", headers=headers)
    assert quizzes_resp.status_code == 200
    assert len(quizzes_resp.json()) >= 1
    print(f"✓ Successfully retrieved {len(quizzes_resp.json())} quiz record(s).")

    # 9. Replace Material A with Material B (Dijkstra / Graph Theory)
    print("\n[Step 9] Testing Material Replacement...")
    pdf_b_bytes = make_pdf([
        "Dijkstra's algorithm is an algorithm for finding the shortest paths between nodes in a graph with non-negative edge weights.",
        "Graph representations commonly include adjacency matrices and adjacency lists depending on sparsity."
    ])
    files_b = {"file": ("graph_theory.pdf", io.BytesIO(pdf_b_bytes), "application/pdf")}
    rep_resp = client.put(f"/projects/{project_id}/materials/{mat_id}/replace", headers=headers, files=files_b)
    assert rep_resp.status_code == 200
    assert rep_resp.json()["filename"] == "graph_theory.pdf"

    for _ in range(25):
        poll = client.get(f"/materials/{mat_id}", headers=headers).json()
        if poll["status"] == "ready":
            break
        time.sleep(0.4)
    assert poll["status"] == "ready"
    print("✓ Replaced material re-indexed successfully.")

    # Verify AI Tutor queries new material vs old material
    tutor_new = client.post(f"/projects/{project_id}/tutor/chat", headers=headers, json={"message": "What does Dijkstra algorithm find?"})
    assert tutor_new.status_code == 200
    assert tutor_new.json()["grounded"] is True
    assert "shortest path" in tutor_new.json()["answer"].lower()
    print("✓ AI Tutor answers accurately using new PDF content.")

    tutor_old = client.post(f"/projects/{project_id}/tutor/chat", headers=headers, json={"message": "What is the average time complexity of QuickSort?"})
    assert tutor_old.status_code == 200
    assert tutor_old.json()["grounded"] is False
    assert "couldn't find enough information" in tutor_old.json()["answer"].lower()
    print("✓ Confirmed stale chunks from previous PDF are purged and no longer retrieved.")

    # 10. Delete Material
    print("\n[Step 10] Testing Material Deletion...")
    del_resp = client.delete(f"/projects/{project_id}/materials/{mat_id}", headers=headers)
    assert del_resp.status_code == 200
    print("✓ Material deleted via API.")

    # Verify material list is empty
    mats_list = client.get(f"/projects/{project_id}/materials", headers=headers).json()
    assert len(mats_list) == 0
    print("✓ Project materials list verified empty.")

    # 11. Verify Activity Events
    print("\n[Step 11] Checking Activity Timeline...")
    act_resp = client.get("/activity?limit=25", headers=headers)
    assert act_resp.status_code == 200
    events = [a["event_type"] for a in act_resp.json()]
    expected_events = ["MATERIAL_UPLOADED", "QUIZ_STARTED", "QUESTION_ANSWERED", "QUIZ_COMPLETED", "MATERIAL_REPLACED", "MATERIAL_DELETED"]
    for ev in expected_events:
        assert ev in events, f"Expected event {ev} not found in activity log: {events}"
        print(f"  ✓ Found activity event: {ev}")

    print("\n==================================================")
    print("  ALL DAY 2 PROMPT 1 FEATURES VERIFIED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_day2_e2e_verification()
