import pytest
from app.models.mastery import ConceptMastery

def test_recommendation_generation_and_completion(client, db_session, user_a_headers):
    # Create space and project
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Data Science"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={
        "name": "ML Foundations",
        "learning_goal": "Master Gradient Descent and Neural Networks"
    }).json()
    project_id = proj["id"]

    me = client.get("/auth/me", headers=user_a_headers).json()
    user_id = me["id"]

    # Seed concepts: one with mistakes and low score, one improving
    m1 = ConceptMastery(
        user_id=user_id,
        project_id=project_id,
        concept="Recursion",
        previous_score=60.0,
        mastery_score=45.0,
        confidence=0.5,
        evidence_count=2,
        recent_mistakes_count=2
    )
    m2 = ConceptMastery(
        user_id=user_id,
        project_id=project_id,
        concept="Functions",
        previous_score=50.0,
        mastery_score=75.0,
        confidence=0.8,
        evidence_count=3,
        recent_mistakes_count=0
    )
    db_session.add_all([m1, m2])
    db_session.commit()

    # Get recommendations
    resp = client.get(f"/projects/{project_id}/recommendations", headers=user_a_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["project_id"] == project_id
    assert data["total_count"] >= 1
    assert data["next_action"] is not None

    # Highest priority should target Recursion due to mistakes & low score
    next_action = data["next_action"]
    assert next_action["concept"] == "Recursion"
    assert next_action["priority"] == "high"
    assert "recursion" in next_action["recommendation"].lower()

    # Complete the recommendation
    rec_id = next_action["id"]
    comp_resp = client.post(
        f"/projects/{project_id}/recommendations/{rec_id}/complete",
        headers=user_a_headers
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["recommendation"]["completed_at"] is not None

    # Check that pending_count decreased
    updated_resp = client.get(f"/projects/{project_id}/recommendations", headers=user_a_headers)
    assert updated_resp.json()["pending_count"] < data["pending_count"]

def test_recommendation_isolation(client, user_a_headers, user_b_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Secure Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Secure Project"}).json()

    resp = client.get(f"/projects/{proj['id']}/recommendations", headers=user_b_headers)
    assert resp.status_code == 404
