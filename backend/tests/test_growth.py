import pytest
from app.models.mastery import ConceptMastery

def test_growth_analysis_classification(client, db_session, user_a_headers):
    """
    Test growth calculation and classification:
    - Functions: 54% -> 72% -> Improving
    - Lists: 68% -> 69% -> Stable
    - Recursion: 61% -> 47% -> Needs Attention
    """
    # Create space and project
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Computer Science"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Algorithms"}).json()
    project_id = proj["id"]

    me = client.get("/auth/me", headers=user_a_headers).json()
    user_id = me["id"]

    # Seed masteries directly to test exact prompt example
    m1 = ConceptMastery(
        user_id=user_id,
        project_id=project_id,
        concept="Functions",
        previous_score=54.0,
        mastery_score=72.0,
        confidence=0.8,
        evidence_count=3,
        recent_mistakes_count=0
    )
    m2 = ConceptMastery(
        user_id=user_id,
        project_id=project_id,
        concept="Lists",
        previous_score=68.0,
        mastery_score=69.0,
        confidence=0.75,
        evidence_count=2,
        recent_mistakes_count=0
    )
    m3 = ConceptMastery(
        user_id=user_id,
        project_id=project_id,
        concept="Recursion",
        previous_score=61.0,
        mastery_score=47.0,
        confidence=0.6,
        evidence_count=3,
        recent_mistakes_count=2
    )
    db_session.add_all([m1, m2, m3])
    db_session.commit()

    resp = client.get(f"/projects/{project_id}/growth", headers=user_a_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["project_id"] == project_id
    assert len(data["concepts"]) == 3

    concept_map = {c["concept"]: c for c in data["concepts"]}

    # Functions check
    assert concept_map["Functions"]["previous_mastery"] == 54.0
    assert concept_map["Functions"]["current_mastery"] == 72.0
    assert concept_map["Functions"]["change"] == 18.0
    assert concept_map["Functions"]["status"] == "Improving"

    # Lists check
    assert concept_map["Lists"]["previous_mastery"] == 68.0
    assert concept_map["Lists"]["current_mastery"] == 69.0
    assert concept_map["Lists"]["change"] == 1.0
    assert concept_map["Lists"]["status"] == "Stable"

    # Recursion check
    assert concept_map["Recursion"]["previous_mastery"] == 61.0
    assert concept_map["Recursion"]["current_mastery"] == 47.0
    assert concept_map["Recursion"]["change"] == -14.0
    assert concept_map["Recursion"]["status"] == "Needs Attention"

    # Summary check
    summary = data["summary"]
    assert summary["total_concepts"] == 3
    assert "Functions" in summary["improving_areas"]
    assert "Lists" in summary["stable_areas"]
    assert "Recursion" in summary["areas_requiring_attention"]
    assert "Recursion" in summary["weak_areas"]

def test_growth_isolation(client, user_a_headers, user_b_headers):
    """
    Test that another user cannot view project growth.
    """
    space = client.post("/spaces", headers=user_a_headers, json={"name": "CS Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Private Growth"}).json()

    resp = client.get(f"/projects/{proj['id']}/growth", headers=user_b_headers)
    assert resp.status_code == 404
