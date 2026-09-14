import os
import time
import io
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import engine
from app.database.base import Base

def run_e2e_verification():
    print("=== STARTING COMPLETE END-TO-END VERIFICATION ===")
    
    # 1. Reset tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    client = TestClient(app)
    
    # 2. Test health check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] 1. GET /health -> 200 OK")
    
    # 3. Register user Alex
    reg_res = client.post("/auth/register", json={
        "name": "Alex Student",
        "email": "alex@study.edu",
        "password": "mypassword123"
    })
    assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
    alex_token = reg_res.json()["access_token"]
    alex_headers = {"Authorization": f"Bearer {alex_token}"}
    print("[PASS] 2. POST /auth/register -> 201 Created (Token received)")
    
    # 4. GET /auth/me
    me_res = client.get("/auth/me", headers=alex_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alex@study.edu"
    print("[PASS] 3. GET /auth/me -> 200 OK (Profile verified)")
    
    # 5. Create Space
    space_res = client.post("/spaces", headers=alex_headers, json={
        "name": "Computer Science",
        "description": "Core CS subjects"
    })
    assert space_res.status_code == 201
    space_id = space_res.json()["id"]
    print(f"[PASS] 4. POST /spaces -> 201 Created (Space ID: {space_id})")
    
    # 6. List Spaces
    spaces_list = client.get("/spaces", headers=alex_headers).json()
    assert len(spaces_list) == 1
    assert spaces_list[0]["name"] == "Computer Science"
    print("[PASS] 5. GET /spaces -> 200 OK (1 space returned)")
    
    # 7. Create Project in Space
    proj_res = client.post(f"/spaces/{space_id}/projects", headers=alex_headers, json={
        "name": "Operating Systems",
        "description": "Kernel and Memory Management",
        "learning_goal": "Understand virtual memory and scheduling"
    })
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]
    print(f"[PASS] 6. POST /spaces/{space_id}/projects -> 201 Created (Project ID: {proj_id})")
    
    # 8. Get Project Details
    proj_get = client.get(f"/projects/{proj_id}", headers=alex_headers)
    assert proj_get.status_code == 200
    assert proj_get.json()["learning_goal"] == "Understand virtual memory and scheduling"
    print(f"[PASS] 7. GET /projects/{proj_id} -> 200 OK")
    
    # 9. Upload PDF Material
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    files = {"file": ("lecture_notes_ch1.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj_id}/materials", headers=alex_headers, files=files)
    assert upload_res.status_code == 201
    mat_data = upload_res.json()
    mat_id = mat_data["id"]
    print(f"[PASS] 8. POST /projects/{proj_id}/materials -> 201 Created (Material ID: {mat_id}, status: {mat_data['status']})")
    
    # 10. Verify Background Processing Transition
    # BackgroundTasks executed by TestClient synchronously or rapidly
    time.sleep(2.5)
    mat_poll = client.get(f"/materials/{mat_id}", headers=alex_headers).json()
    assert mat_poll["status"] == "ready", f"Expected ready, got {mat_poll['status']}"
    print(f"[PASS] 9. Background Processing -> Transitioned to 'ready' successfully!")
    
    # 11. Activity Tracking Feed
    activity_res = client.get("/activity", headers=alex_headers)
    assert activity_res.status_code == 200
    events = [e["event_type"] for e in activity_res.json()]
    print(f"[INFO] Recorded Activity Events: {events}")
    assert "SPACE_CREATED" in events
    assert "PROJECT_CREATED" in events
    assert "MATERIAL_UPLOADED" in events
    assert "MATERIAL_PROCESSING_STARTED" in events
    assert "MATERIAL_PROCESSED" in events
    print("[PASS] 10. GET /activity -> All 5 sequential lifecycle events verified")
    
    # 12. Security Isolation: User Bob
    bob_reg = client.post("/auth/register", json={
        "name": "Bob Intruder",
        "email": "bob@malicious.com",
        "password": "password123"
    })
    bob_token = bob_reg.json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}
    
    # Bob attempts unauthorized access
    assert client.get(f"/spaces/{space_id}", headers=bob_headers).status_code == 404
    assert client.put(f"/spaces/{space_id}", headers=bob_headers, json={"name": "Hacked"}).status_code == 404
    assert client.delete(f"/spaces/{space_id}", headers=bob_headers).status_code == 404
    assert client.get(f"/spaces/{space_id}/projects", headers=bob_headers).status_code == 404
    assert client.get(f"/projects/{proj_id}", headers=bob_headers).status_code == 404
    assert client.get(f"/materials/{mat_id}", headers=bob_headers).status_code == 404
    
    # Bob tries to upload to Alex's project
    bad_upload = client.post(f"/projects/{proj_id}/materials", headers=bob_headers, files=files)
    assert bad_upload.status_code == 404
    print("[PASS] 11. Security Isolation -> Cross-user access strictly blocked with 404 across Spaces, Projects, Materials")

    print("\n=== ALL END-TO-END VERIFICATION CHECKS PASSED PERFECTLY ===")

if __name__ == "__main__":
    run_e2e_verification()
