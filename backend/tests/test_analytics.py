import io
import time
from datetime import datetime, timezone
from fpdf import FPDF
from app.models.activity_event import ActivityEvent, ActivityEventType
from app.models.mastery import ConceptMastery
from app.models.quiz import Quiz, QuizQuestion, QuizAnswer, QuizStatus
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentResponse, AssessmentStatus

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


def test_activity_event_creation(client, db_session, user_a_headers):
    # 1. Create space -> SPACE_CREATED
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Science Space"}).json()
    assert "id" in space

    # 2. Create project -> PROJECT_CREATED
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Physics Project"}).json()
    assert "id" in proj

    # 3. Access project -> PROJECT_ACCESSED
    acc_res = client.get(f"/projects/{proj['id']}", headers=user_a_headers)
    assert acc_res.status_code == 200

    # 4. View growth -> GROWTH_VIEWED
    growth_res = client.get(f"/projects/{proj['id']}/growth", headers=user_a_headers)
    assert growth_res.status_code == 200

    # 5. Check activity list
    act_res = client.get("/activity", headers=user_a_headers)
    assert act_res.status_code == 200
    events = act_res.json()
    types = [e["event_type"] for e in events]

    assert ActivityEventType.SPACE_CREATED.value in types
    assert ActivityEventType.PROJECT_CREATED.value in types
    assert ActivityEventType.PROJECT_ACCESSED.value in types
    assert ActivityEventType.GROWTH_VIEWED.value in types

    # Check non-sensitive metadata preservation
    proj_acc_event = next(e for e in events if e["event_type"] == ActivityEventType.PROJECT_ACCESSED.value)
    assert proj_acc_event["metadata"]["project_name"] == "Physics Project"


def test_activity_filtering(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Engineering"}).json()
    p1 = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Robotics"}).json()
    p2 = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Aerospace"}).json()

    # Access both
    client.get(f"/projects/{p1['id']}", headers=user_a_headers)
    client.get(f"/projects/{p2['id']}", headers=user_a_headers)

    # Filter by project 1
    res_p1 = client.get(f"/activity?project_id={p1['id']}", headers=user_a_headers)
    assert res_p1.status_code == 200
    events_p1 = res_p1.json()
    assert len(events_p1) >= 2  # PROJECT_CREATED and PROJECT_ACCESSED
    assert all(e["project_id"] == p1["id"] for e in events_p1)

    # Filter by event_type
    res_type = client.get(f"/activity?event_type={ActivityEventType.PROJECT_CREATED.value}", headers=user_a_headers)
    assert res_type.status_code == 200
    events_type = res_type.json()
    assert all(e["event_type"] == ActivityEventType.PROJECT_CREATED.value for e in events_type)


def test_empty_analytics_state(client, user_a_headers):
    # Completely new user with 0 spaces/projects
    res = client.get("/analytics/global", headers=user_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_learning_activity"] == 0
    assert data["active_days"] == 0
    assert data["total_spaces"] == 0
    assert data["total_projects"] == 0
    assert data["overall_mastery"] == 0.0
    assert data["average_assessment_performance"] is None
    assert data["concepts_improving"] == 0
    assert data["concepts_requiring_attention"] == 0
    assert data["tutor_interactions"] == 0
    assert data["questions_asked"] == 0
    assert data["quiz_activity"]["quizzes_started"] == 0
    assert data["quiz_activity"]["quiz_accuracy"] == 0.0
    assert data["projects_breakdown"] == []
    assert data["recent_activities"] == []
    assert len(data["learning_activity_over_time"]) == 14


def test_project_analytics_aggregation(client, db_session, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "CS Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Data Structures"}).json()
    p_id = proj["id"]

    # Upload material
    pdf_bytes = make_sample_pdf([
        "Arrays and Linked Lists are basic linear data structures in computer science.",
        "A Stack is a LIFO data structure whereas a Queue is a FIFO data structure."
    ])
    files = {"file": ("data_structures.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{p_id}/materials", headers=user_a_headers, files=files)
    mat_id = upload_res.json()["id"]
    poll_for_ready(client, user_a_headers, mat_id)

    # Ask tutor question
    tutor_res = client.post(f"/projects/{p_id}/tutor/chat", headers=user_a_headers, json={"message": "What is a Stack?"})
    assert tutor_res.status_code == 200

    quiz_res = client.post(f"/projects/{p_id}/quiz/start", headers=user_a_headers, json={"total_questions": 2})
    assert quiz_res.status_code == 201
    q_data = quiz_res.json()
    quiz_id = q_data.get("quiz_id") or q_data.get("id") or (q_data.get("quiz") or {}).get("id")
    question_id = q_data["current_question"]["id"]

    # Answer question
    ans_res = client.post(
        f"/projects/{p_id}/quiz/{quiz_id}/answer",
        headers=user_a_headers,
        json={"question_id": question_id, "answer_text": q_data["current_question"]["options"][0]}
    )
    assert ans_res.status_code == 200

    # Query project analytics
    res = client.get(f"/projects/{p_id}/analytics", headers=user_a_headers)
    assert res.status_code == 200
    analytics = res.json()

    assert analytics["project_id"] == p_id
    assert analytics["project_name"] == "Data Structures"

    # Activity verification
    act = analytics["activity"]
    assert act["total_events"] >= 3
    assert act["tutor_questions"] >= 1
    assert act["quiz_attempts"] >= 1
    assert act["questions_answered"] >= 1
    assert act["material_interactions"] >= 1

    # Growth & AI activity
    growth = analytics["growth"]
    assert len(growth["activity_over_time"]) == 14

    ai = analytics["ai_activity"]
    assert ai["tutor_interactions"] >= 1


def test_global_analytics_aggregation(client, user_a_headers):
    s1 = client.post("/spaces", headers=user_a_headers, json={"name": "Space One"}).json()
    s2 = client.post("/spaces", headers=user_a_headers, json={"name": "Space Two"}).json()

    p1 = client.post(f"/spaces/{s1['id']}/projects", headers=user_a_headers, json={"name": "Project Alpha"}).json()
    p2 = client.post(f"/spaces/{s2['id']}/projects", headers=user_a_headers, json={"name": "Project Beta"}).json()

    # Query global analytics
    res = client.get("/analytics/global", headers=user_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_spaces"] == 2
    assert data["total_projects"] == 2
    assert len(data["projects_breakdown"]) == 2
    proj_names = [p["project_name"] for p in data["projects_breakdown"]]
    assert "Project Alpha" in proj_names
    assert "Project Beta" in proj_names


def test_user_data_isolation(client, user_a_headers, user_b_headers):
    # User A creates space and project
    s_a = client.post("/spaces", headers=user_a_headers, json={"name": "User A Private Space"}).json()
    p_a = client.post(f"/spaces/{s_a['id']}/projects", headers=user_a_headers, json={"name": "User A Confidential Project"}).json()

    # User B attempts to access User A's project analytics -> 404 (or 403)
    res_b_proj = client.get(f"/projects/{p_a['id']}/analytics", headers=user_b_headers)
    assert res_b_proj.status_code in [403, 404]

    # User B attempts to view User A's project activity -> 404 (or 403)
    res_b_act = client.get(f"/activity?project_id={p_a['id']}", headers=user_b_headers)
    assert res_b_act.status_code in [403, 404]

    # User B checks global analytics -> 0 spaces, 0 projects
    res_b_global = client.get("/analytics/global", headers=user_b_headers)
    assert res_b_global.status_code == 200
    assert res_b_global.json()["total_spaces"] == 0
    assert res_b_global.json()["total_projects"] == 0
    assert res_b_global.json()["total_learning_activity"] == 0
