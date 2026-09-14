import io
import time
from fpdf import FPDF
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentResponse, AssessmentStatus
from app.models.activity_event import ActivityEvent, ActivityEventType

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

def test_start_assessment_without_materials_fails(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Empty Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Empty Project"}).json()

    res = client.post(f"/projects/{proj['id']}/assessments/start", headers=user_a_headers, json={"total_questions": 2})
    assert res.status_code == 400
    assert "no processed materials" in res.json()["detail"].lower()

def test_open_ended_assessment_flow_and_evaluation(client, db_session, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "CS Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Data Structures"}).json()

    # Upload learning material
    pdf_bytes = make_sample_pdf([
        "Trees are hierarchical data structures consisting of nodes with parent-child relationships.",
        "Binary Search Trees maintain a property where all left descendants are smaller and right descendants are larger than the root node."
    ])
    files = {"file": ("trees_intro.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj['id']}/materials", headers=user_a_headers, files=files)
    mat_id = upload_res.json()["id"]
    poll_for_ready(client, user_a_headers, mat_id)

    # 1. Start Assessment
    start_res = client.post(f"/projects/{proj['id']}/assessments/start", headers=user_a_headers, json={"total_questions": 2})
    assert start_res.status_code == 201
    assessment = start_res.json()
    assessment_id = assessment["id"]
    assert assessment["status"] == "in_progress"
    assert len(assessment["questions"]) == 2

    q1 = assessment["questions"][0]
    assert q1["question_text"] is not None
    assert q1["concept"] is not None

    # Check Activity: ASSESSMENT_STARTED
    started_ev = (
        db_session.query(ActivityEvent)
        .filter(ActivityEvent.event_type == ActivityEventType.ASSESSMENT_STARTED.value)
        .order_by(ActivityEvent.created_at.desc())
        .first()
    )
    assert started_ev is not None
    assert started_ev.metadata_json["assessment_id"] == assessment_id

    # 2. Submit First Response (Thorough, accurate answer)
    student_response_1 = (
        "Trees are non-linear hierarchical data structures where each node contains a value "
        "and links to child nodes, forming parent-child relationships starting from a root node."
    )
    sub1_res = client.post(
        f"/projects/{proj['id']}/assessments/{assessment_id}/submit",
        headers=user_a_headers,
        json={"question_id": q1["id"], "response_text": student_response_1}
    )
    assert sub1_res.status_code == 200
    eval1 = sub1_res.json()

    # Structured evaluation assertions
    assert 0 <= eval1["score"] <= 100
    assert eval1["score"] >= 65  # Good response should get high score
    assert isinstance(eval1["understanding"], str) and len(eval1["understanding"]) > 0
    assert isinstance(eval1["accuracy"], str) and len(eval1["accuracy"]) > 0
    assert isinstance(eval1["strengths"], list) and len(eval1["strengths"]) > 0
    assert isinstance(eval1["missing_concepts"], list)
    assert isinstance(eval1["feedback"], str) and len(eval1["feedback"]) > 0
    assert isinstance(eval1["concepts"], list) and len(eval1["concepts"]) > 0

    # Verify duplicate submission is rejected
    dup_res = client.post(
        f"/projects/{proj['id']}/assessments/{assessment_id}/submit",
        headers=user_a_headers,
        json={"question_id": q1["id"], "response_text": student_response_1}
    )
    assert dup_res.status_code == 400
    assert "already been answered" in dup_res.json()["detail"]

    # 3. Submit Second Response (Very brief answer)
    q2 = assessment["questions"][1]
    student_response_2 = "Trees have nodes."
    sub2_res = client.post(
        f"/projects/{proj['id']}/assessments/{assessment_id}/submit",
        headers=user_a_headers,
        json={"question_id": q2["id"], "response_text": student_response_2}
    )
    assert sub2_res.status_code == 200
    eval2 = sub2_res.json()
    assert eval2["score"] < 60  # Brief response should get lower score
    assert len(eval2["missing_concepts"]) > 0
    assert "too brief" in eval2["feedback"].lower() or "misses" in eval2["feedback"].lower()

    # 4. Check Assessment Detail (Now completed)
    detail_res = client.get(f"/projects/{proj['id']}/assessments/{assessment_id}", headers=user_a_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["status"] == "completed"
    assert detail["overall_score"] is not None
    assert len(detail["responses"]) == 2

    # 5. List Assessments
    list_res = client.get(f"/projects/{proj['id']}/assessments", headers=user_a_headers)
    assert list_res.status_code == 200
    assert any(a["id"] == assessment_id for a in list_res.json())

def test_assessment_isolation(client, user_a_headers, user_b_headers):
    space_a = client.post("/spaces", headers=user_a_headers, json={"name": "Space A"}).json()
    proj_a = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={"name": "Proj A"}).json()

    pdf_bytes = make_sample_pdf(["Operating systems coordinate hardware and software resources."])
    files = {"file": ("os.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj_a['id']}/materials", headers=user_a_headers, files=files)
    poll_for_ready(client, user_a_headers, upload_res.json()["id"])

    # User A starts assessment
    start_res = client.post(f"/projects/{proj_a['id']}/assessments/start", headers=user_a_headers, json={"total_questions": 1})
    assessment_id = start_res.json()["id"]

    # User B cannot access User A's assessment
    assert client.get(f"/projects/{proj_a['id']}/assessments/{assessment_id}", headers=user_b_headers).status_code == 404
    assert client.get(f"/projects/{proj_a['id']}/assessments", headers=user_b_headers).status_code == 404

    # User B cannot submit to User A's assessment
    sub_res = client.post(
        f"/projects/{proj_a['id']}/assessments/{assessment_id}/submit",
        headers=user_b_headers,
        json={"question_id": 1, "response_text": "An operating system manages hardware."}
    )
    assert sub_res.status_code == 404
