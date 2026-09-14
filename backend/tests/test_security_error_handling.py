import io
import pytest
from app.models.space import Space
from app.models.project import Project
from app.models.material import Material, MaterialStatus

def test_multitenant_space_and_project_isolation(client, user_a_headers, user_b_headers):
    """
    Verify User B cannot view, edit, or delete User A's Spaces and Projects.
    """
    # 1. User A creates a space and project
    space_res = client.post("/spaces", headers=user_a_headers, json={"name": "Alice Space", "description": "Private"})
    assert space_res.status_code == 201
    space_a_id = space_res.json()["id"]

    proj_res = client.post(f"/spaces/{space_a_id}/projects", headers=user_a_headers, json={
        "name": "Alice Project",
        "description": "Private project",
        "learning_goal": "Goal A"
    })
    assert proj_res.status_code == 201
    proj_a_id = proj_res.json()["id"]

    # 2. User B attempts to access User A's Space
    res = client.get(f"/spaces/{space_a_id}", headers=user_b_headers)
    assert res.status_code == 404

    res = client.put(f"/spaces/{space_a_id}", headers=user_b_headers, json={"name": "Hacked Space"})
    assert res.status_code == 404

    res = client.delete(f"/spaces/{space_a_id}", headers=user_b_headers)
    assert res.status_code == 404

    # 3. User B attempts to access User A's Project
    res = client.get(f"/projects/{proj_a_id}", headers=user_b_headers)
    assert res.status_code == 404

    res = client.put(f"/projects/{proj_a_id}", headers=user_b_headers, json={"name": "Hacked Project"})
    assert res.status_code == 404

    res = client.delete(f"/projects/{proj_a_id}", headers=user_b_headers)
    assert res.status_code == 404


def test_multitenant_tutor_and_materials_isolation(client, user_a_headers, user_b_headers):
    """
    Verify User B cannot access materials, chat with tutor, or manipulate resources in User A's project.
    """
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Alice Bio"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={
        "name": "Bio Project",
        "learning_goal": "Understand cells"
    }).json()
    proj_id = proj["id"]

    # User B tries to view materials list in User A's project
    res = client.get(f"/projects/{proj_id}/materials", headers=user_b_headers)
    assert res.status_code == 404

    # User B tries to upload material to User A's project
    fake_pdf = b"%PDF-1.4 fake pdf content"
    res = client.post(
        f"/projects/{proj_id}/materials",
        headers=user_b_headers,
        files={"file": ("malicious.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    )
    assert res.status_code == 404

    # User B tries to talk to tutor in User A's project
    res = client.post(f"/projects/{proj_id}/tutor/chat", headers=user_b_headers, json={
        "message": "Tell me about Alice's notes"
    })
    assert res.status_code == 404


def test_multitenant_quiz_mastery_growth_analytics_isolation(client, user_a_headers, user_b_headers):
    """
    Verify User B cannot view or tamper with User A's quizzes, mastery, growth, recommendations, or analytics.
    """
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Alice Math"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={
        "name": "Calculus",
        "learning_goal": "Integrals"
    }).json()
    proj_id = proj["id"]

    # Quizzes
    res = client.get(f"/projects/{proj_id}/quizzes", headers=user_b_headers)
    assert res.status_code == 404

    # Assessments
    res = client.get(f"/projects/{proj_id}/assessments", headers=user_b_headers)
    assert res.status_code == 404

    # Mastery
    res = client.get(f"/projects/{proj_id}/mastery", headers=user_b_headers)
    assert res.status_code == 404

    # Growth
    res = client.get(f"/projects/{proj_id}/growth", headers=user_b_headers)
    assert res.status_code == 404

    # Recommendations
    res = client.get(f"/projects/{proj_id}/recommendations", headers=user_b_headers)
    assert res.status_code == 404

    # Project Analytics
    res = client.get(f"/projects/{proj_id}/analytics", headers=user_b_headers)
    assert res.status_code == 404


def test_admin_rbac_rejection(client, user_a_headers):
    """
    Verify that regular users receive 403 Forbidden when attempting to access admin endpoints.
    """
    admin_endpoints = [
        "/admin/dashboard/overview",
        "/admin/users",
        "/admin/ai-usage",
        "/admin/ai-evaluation",
        "/admin/system-health"
    ]
    for ep in admin_endpoints:
        res = client.get(ep, headers=user_a_headers)
        assert res.status_code == 403, f"Expected 403 for {ep}, got {res.status_code}"
        assert "detail" in res.json()


def test_auth_token_validation(client):
    """
    Verify unauthenticated, invalid, or malformed tokens are properly rejected with 401.
    """
    # No auth header
    res = client.get("/spaces")
    assert res.status_code == 401

    # Fake/invalid bearer token
    res = client.get("/spaces", headers={"Authorization": "Bearer totally_fake_token_value_xyz"})
    assert res.status_code == 401

    # Malformed header
    res = client.get("/spaces", headers={"Authorization": "InvalidScheme token"})
    assert res.status_code == 401


def test_input_validation_and_no_stack_traces(client, user_a_headers):
    """
    Verify robust handling of invalid inputs and that internal python tracebacks are not leaked.
    """
    # Non-existent project
    res = client.get("/projects/999999", headers=user_a_headers)
    assert res.status_code == 404
    body_str = res.text
    assert "Traceback (most recent call last)" not in body_str

    # Non-existent space
    res = client.get("/spaces/999999", headers=user_a_headers)
    assert res.status_code == 404
    assert "Traceback (most recent call last)" not in res.text

    # Empty payload for project creation
    res = client.post("/spaces/1/projects", headers=user_a_headers, json={})
    assert res.status_code == 422
    assert "Traceback (most recent call last)" not in res.text


def test_edge_cases_zero_data_graceful_handling(client, user_a_headers):
    """
    Verify system handles brand-new projects with zero data gracefully without crashing or throwing 500s.
    """
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Fresh Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={
        "name": "Empty Project",
        "learning_goal": "Start fresh"
    }).json()
    proj_id = proj["id"]

    # 1. Growth with zero data
    growth_res = client.get(f"/projects/{proj_id}/growth", headers=user_a_headers)
    assert growth_res.status_code == 200
    g_data = growth_res.json()
    assert g_data["overall_progress"] == 0.0
    assert isinstance(g_data["concepts"], list)

    # 2. Recommendations with zero data
    rec_res = client.get(f"/projects/{proj_id}/recommendations", headers=user_a_headers)
    assert rec_res.status_code == 200
    r_data = rec_res.json()
    assert "recommendations" in r_data

    # 3. Analytics with zero data
    analytics_res = client.get(f"/projects/{proj_id}/analytics", headers=user_a_headers)
    assert analytics_res.status_code == 200
    a_data = analytics_res.json()
    assert a_data["activity"]["learning_sessions"] >= 0

    # 4. Global analytics with empty user
    global_res = client.get("/analytics/global", headers=user_a_headers)
    assert global_res.status_code == 200
    assert global_res.json()["total_projects"] >= 1
