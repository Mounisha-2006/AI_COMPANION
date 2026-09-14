import io
import time
from fpdf import FPDF
from app.models.activity_event import ActivityEvent, ActivityEventType
from app.models.quiz import QuizQuestion

def make_sample_pdf(pages_text):
    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(w=0, h=10, text=text)
    return bytes(pdf.output())

def poll_for_ready(client, headers, mat_id, max_wait_sec=10):
    start = time.time()
    while time.time() - start < max_wait_sec:
        res = client.get(f"/materials/{mat_id}", headers=headers)
        if res.status_code == 200 and res.json()["status"] == "ready":
            return res.json()
        time.sleep(0.3)
    res = client.get(f"/materials/{mat_id}", headers=headers)
    return res.json()

def test_concept_mastery_tracking(client, db_session, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Programming"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Python Mastery"}).json()
    proj_id = proj["id"]

    # 1. Initially mastery is empty
    m_init = client.get(f"/projects/{proj_id}/mastery", headers=user_a_headers).json()
    assert m_init["project_id"] == proj_id
    assert len(m_init["concepts"]) == 0

    # 2. Upload material with Functions and Recursion
    pdf_bytes = make_sample_pdf([
        "Functions in Python are defined using the def keyword to encapsulate reusable logic.",
        "Recursion is a technique where a function calls itself directly to solve smaller instances of a problem."
    ])
    files = {"file": ("python_funcs.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)
    mat_id = upload_res.json()["id"]
    poll_for_ready(client, user_a_headers, mat_id)

    # 3. Take a Quiz and answer a question correctly
    quiz_res = client.post(f"/projects/{proj_id}/quiz/start", headers=user_a_headers, json={"total_questions": 1}).json()
    quiz_id = quiz_res["id"]
    q1 = quiz_res["current_question"]

    db_q1 = db_session.query(QuizQuestion).filter(QuizQuestion.id == q1["id"]).first()
    client.post(f"/projects/{proj_id}/quiz/{quiz_id}/answer", headers=user_a_headers, json={
        "question_id": q1["id"],
        "answer_text": db_q1.correct_answer
    })

    # Verify Concept Mastery was recorded from Quiz
    m_after_quiz = client.get(f"/projects/{proj_id}/mastery", headers=user_a_headers).json()
    assert len(m_after_quiz["concepts"]) >= 1
    c1 = next(c for c in m_after_quiz["concepts"] if c["concept"] == q1["concept"].capitalize())
    assert c1["mastery_score"] == 100.0
    assert c1["evidence_count"] == 1
    assert c1["confidence"] > 0

    # Verify MASTERY_UPDATED activity event
    ev = (
        db_session.query(ActivityEvent)
        .filter(ActivityEvent.event_type == ActivityEventType.MASTERY_UPDATED.value)
        .order_by(ActivityEvent.created_at.desc())
        .first()
    )
    assert ev is not None
    assert ev.metadata_json["concept"] == q1["concept"].capitalize()

    # 4. Take an Open-Ended Assessment and submit a response for another concept
    assess_res = client.post(f"/projects/{proj_id}/assessments/start", headers=user_a_headers, json={"total_questions": 1}).json()
    assess_id = assess_res["id"]
    aq1 = assess_res["questions"][0]

    # Submit weak/poor answer to test "areas_needing_attention"
    client.post(f"/projects/{proj_id}/assessments/{assess_id}/submit", headers=user_a_headers, json={
        "question_id": aq1["id"],
        "response_text": "Not sure."
    })

    # Verify Mastery updated with assessment evidence
    m_after_assess = client.get(f"/projects/{proj_id}/mastery", headers=user_a_headers).json()
    assert len(m_after_assess["concepts"]) >= 1
    # Check that low scoring concept was added to areas_needing_attention
    assert len(m_after_assess["areas_needing_attention"]) >= 1
    assert aq1["concept"].capitalize() in m_after_assess["areas_needing_attention"]

def test_mastery_isolation(client, user_a_headers, user_b_headers):
    space_a = client.post("/spaces", headers=user_a_headers, json={"name": "Space A"}).json()
    proj_a = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={"name": "Proj A"}).json()

    # User B cannot access User A's mastery
    res = client.get(f"/projects/{proj_a['id']}/mastery", headers=user_b_headers)
    assert res.status_code == 404
