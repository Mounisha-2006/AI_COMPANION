import pytest
from app.services.auth_service import AuthService
from app.models.user import User
from app.models.activity_event import ActivityEvent, ActivityEventType
from app.models.ai_usage import AIUsage
from app.models.mastery import ConceptMastery
from app.models.quiz import Quiz, QuizQuestion, QuizAnswer, QuizStatus
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentResponse, AssessmentStatus
from app.core.security import hash_password
from datetime import datetime, timezone

def create_admin(db_session, client, email="admin_test@example.com", password="AdminPassword123!"):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            name="Platform Admin",
            email=email,
            password_hash=hash_password(password),
            role="ADMIN"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def test_admin_authorization_success(client, db_session):
    """
    Verify that an authenticated user with role == ADMIN can access all admin endpoints.
    """
    headers, admin_user = create_admin(db_session, client)

    # Overview
    res = client.get("/admin/dashboard/overview", headers=headers)
    assert res.status_code == 200
    assert "kpis" in res.json()

    # Users list
    res = client.get("/admin/users", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # AI Usage
    res = client.get("/admin/ai-usage", headers=headers)
    assert res.status_code == 200
    assert "feature_breakdown" in res.json()

    # AI Evaluation
    res = client.get("/admin/ai-evaluation", headers=headers)
    assert res.status_code == 200
    assert "tutor_evaluation" in res.json()

    # System Health
    res = client.get("/admin/system-health", headers=headers)
    assert res.status_code == 200
    assert res.json()["api_status"] == "healthy"


def test_normal_user_forbidden(client, user_a_headers):
    """
    Verify that a normal user receives 403 Forbidden on all admin endpoints.
    """
    # 1. Overview forbidden
    res = client.get("/admin/dashboard/overview", headers=user_a_headers)
    assert res.status_code == 403
    assert "Admin privileges required" in res.json()["detail"]

    # 2. Users list forbidden
    res = client.get("/admin/users", headers=user_a_headers)
    assert res.status_code == 403

    # 3. User inspect forbidden
    res = client.get("/admin/users/1", headers=user_a_headers)
    assert res.status_code == 403

    # 4. AI usage forbidden
    res = client.get("/admin/ai-usage", headers=user_a_headers)
    assert res.status_code == 403

    # 5. AI evaluation forbidden
    res = client.get("/admin/ai-evaluation", headers=user_a_headers)
    assert res.status_code == 403

    # 6. System health forbidden
    res = client.get("/admin/system-health", headers=user_a_headers)
    assert res.status_code == 403


def test_unauthenticated_unauthorized(client):
    """
    Verify that unauthenticated requests receive 401 Unauthorized.
    """
    res = client.get("/admin/dashboard/overview")
    assert res.status_code == 401

    res = client.get("/admin/users")
    assert res.status_code == 401

    res = client.get("/admin/system-health")
    assert res.status_code == 401


def test_admin_dashboard_overview_metrics(client, db_session, user_a_headers):
    """
    Verify that the Admin Overview returns valid aggregate KPIs and recent feeds.
    """
    admin_headers, _ = create_admin(db_session, client)

    # Normal user creates space and project
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Math Space"}).json()
    client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Linear Algebra"}).json()

    res = client.get("/admin/dashboard/overview", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    kpis = data["kpis"]
    assert kpis["total_users"] >= 2  # Admin + User A
    assert kpis["total_spaces"] >= 1
    assert kpis["total_projects"] >= 1
    assert "recent_users" in data
    assert "recent_projects" in data
    assert "recent_activity_events" in data
    assert "recent_material_events" in data


def test_admin_user_inspection_and_isolation(client, db_session, user_a_headers, user_b_headers):
    """
    Verify admin user listing and deep observation-only inspection with strict data isolation.
    """
    admin_headers, _ = create_admin(db_session, client)

    # User A creates space & project
    space_a = client.post("/spaces", headers=user_a_headers, json={"name": "Alice Chemistry"}).json()
    proj_a = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={"name": "Organic Chem"}).json()

    # User B creates space & project
    space_b = client.post("/spaces", headers=user_b_headers, json={"name": "Bob History"}).json()
    proj_b = client.post(f"/spaces/{space_b['id']}/projects", headers=user_b_headers, json={"name": "Ancient Rome"}).json()

    # List users
    users_res = client.get("/admin/users", headers=admin_headers)
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) >= 3

    # Inspect User A
    user_a = db_session.query(User).filter(User.email == "alice@example.com").first()
    inspect_res = client.get(f"/admin/users/{user_a.id}", headers=admin_headers)
    assert inspect_res.status_code == 200
    data = inspect_res.json()

    assert data["user"]["email"] == "alice@example.com"
    # Verify strict isolation: Alice has Organic Chem, but NOT Ancient Rome
    project_names = [p["name"] for p in data["projects"]]
    assert "Organic Chem" in project_names
    assert "Ancient Rome" not in project_names

    # Verify spaces isolation
    space_names = [s["name"] for s in data["spaces"]]
    assert "Alice Chemistry" in space_names
    assert "Bob History" not in space_names


def test_ai_usage_and_disclosure(client, db_session):
    """
    Verify AI usage logging and that unrecorded tokens/costs explicitly display 'Not available' without inventing values.
    """
    admin_headers, admin_user = create_admin(db_session, client)

    # Seed AIUsage records
    u1 = AIUsage(
        user_id=admin_user.id,
        project_id=1,
        feature="tutor_answer",
        model="local-grounded-synthesizer",
        latency_ms=120,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        success=True,
        created_at=datetime.now(timezone.utc)
    )
    u2 = AIUsage(
        user_id=admin_user.id,
        project_id=1,
        feature="quiz_generation",
        model="local-question-synthesizer",
        latency_ms=250,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        success=False,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add_all([u1, u2])
    db_session.commit()

    res = client.get("/admin/ai-usage", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_requests"] >= 2
    assert "tutor_answer" in data["feature_breakdown"]
    assert "quiz_generation" in data["feature_breakdown"]
    assert data["error_count"] >= 1

    # Check token usage disclosure: must be "Not available" when none recorded
    assert data["token_usage"]["display_text"] == "Not available"
    assert data["token_usage"]["total_tokens"] is None

    # Check cost disclosure: must be "Not available" (never invent values)
    assert data["estimated_cost"]["display_text"] == "Not available"
    assert data["estimated_cost"]["amount"] is None


def test_ai_evaluation_and_benchmark_runner(client, db_session):
    """
    Verify that AI evaluation metrics and benchmark tests run and return results.
    """
    admin_headers, _ = create_admin(db_session, client)

    # 1. Get AI evaluation
    res = client.get("/admin/ai-evaluation", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert "tutor_evaluation" in data
    assert "assessment_evaluation" in data
    assert "benchmark_results" in data
    assert len(data["benchmark_results"]) >= 4

    # Check benchmark items structure
    bm = data["benchmark_results"][0]
    assert "test_name" in bm
    assert "category" in bm
    assert "status" in bm
    assert "latency_ms" in bm
    assert bm["status"] in ["PASS", "FAIL"]

    # 2. Run evaluation benchmark suite via POST
    run_res = client.post("/admin/ai-evaluation/run", headers=admin_headers)
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert len(run_data["benchmark_results"]) >= 4


def test_system_health_endpoint_and_no_leaked_secrets(client, db_session):
    """
    Verify lightweight system health endpoint and ensure zero secrets/passwords are exposed.
    """
    admin_headers, _ = create_admin(db_session, client)

    res = client.get("/admin/system-health", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["api_status"] == "healthy"
    assert data["database"]["status"] == "connected"
    assert "latency_ms" in data["database"]
    assert data["ai_provider"]["status"] == "operational"
    assert "background_queue" in data
    assert "average_ai_latency_ms" in data
    assert "ai_error_rate" in data

    # Verify zero secrets or credentials leaked
    payload_str = str(data).lower()
    assert "password" not in payload_str
    assert "secret" not in payload_str
    assert "aiza" not in payload_str  # No Google API key prefix
    assert "sk-" not in payload_str   # No OpenAI key prefix
