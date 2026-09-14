import io
import time
from fpdf import FPDF
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import engine, SessionLocal
from app.database.base import Base
from app.models.document_chunk import DocumentChunk
import app.services.material_service as mat_service

def make_test_pdf(pages_text):
    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(w=0, h=10, text=text)
    return bytes(pdf.output())

def run_tutor_e2e():
    print("=== STARTING AI TUTOR & RAG END-TO-END VERIFICATION ===")
    
    # 1. Reset tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    mat_service.SessionLocal = SessionLocal
    
    client = TestClient(app)
    
    # 2. Register Alex
    reg_res = client.post("/auth/register", json={
        "name": "Alex Distributed",
        "email": "alex@consensus.edu",
        "password": "strongpassword123"
    })
    assert reg_res.status_code == 201
    alex_token = reg_res.json()["access_token"]
    alex_headers = {"Authorization": f"Bearer {alex_token}"}
    print("[PASS] 1. Registered user Alex & retrieved access token")
    
    # 3. Create Space
    space_res = client.post("/spaces", headers=alex_headers, json={
        "name": "Distributed Systems",
        "description": "Consensus & fault tolerance"
    })
    assert space_res.status_code == 201
    space_id = space_res.json()["id"]
    print(f"[PASS] 2. Created Space (ID: {space_id})")
    
    # 4. Create Project
    proj_res = client.post(f"/spaces/{space_id}/projects", headers=alex_headers, json={
        "name": "Consensus Protocols",
        "learning_goal": "Understand Paxos and Raft consensus algorithms",
        "description": "Log replication and leader election"
    })
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]
    print(f"[PASS] 3. Created Project (ID: {proj_id})")
    
    # 5. Upload real 2-page PDF
    pdf_bytes = make_test_pdf([
        "Page 1: Raft is a consensus algorithm designed as an alternative to Multi-Paxos. Raft divides consensus into leader election, log replication, and safety.",
        "Page 2: In Raft leader election, randomized election timers between 150ms and 300ms are used to prevent split votes among candidates."
    ])
    files = {"file": ("raft_consensus.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj_id}/materials", headers=alex_headers, files=files)
    assert upload_res.status_code == 201
    mat_id = upload_res.json()["id"]
    print(f"[PASS] 4. Uploaded PDF Material (ID: {mat_id}, filename: raft_consensus.pdf)")
    
    # 6. Verify processing status is ready
    mat_res = client.get(f"/materials/{mat_id}", headers=alex_headers).json()
    assert mat_res["status"] == "ready", f"Expected ready, got {mat_res['status']}"
    print(f"[PASS] 5. Material processing finished -> status: ready")
    
    # Verify chunks in DB
    db = SessionLocal()
    chunks = db.query(DocumentChunk).filter(DocumentChunk.material_id == mat_id).all()
    assert len(chunks) >= 2
    assert any(c.page_number == 1 for c in chunks)
    assert any(c.page_number == 2 for c in chunks)
    assert all(c.embedding is not None for c in chunks)
    db.close()
    print(f"[PASS] 6. Document chunks created with 1-indexed pages and vector embeddings")
    
    # 7. Ask grounded question supported by Page 2
    question_1 = "How does Raft avoid split votes during leader election?"
    tutor_res1 = client.post(f"/projects/{proj_id}/tutor/chat", headers=alex_headers, json={
        "message": question_1
    })
    assert tutor_res1.status_code == 200
    ans1 = tutor_res1.json()
    print(f"\nQ: {question_1}")
    print(f"A: {ans1['answer']}")
    print(f"Sources: {ans1['sources']}")
    print(f"Grounded: {ans1['grounded']}")
    
    assert ans1["grounded"] is True
    assert len(ans1["sources"]) > 0
    assert any(s["filename"] == "raft_consensus.pdf" and s["page"] == 2 for s in ans1["sources"])
    assert "randomized" in ans1["answer"].lower() or "timer" in ans1["answer"].lower() or "split votes" in ans1["answer"].lower()
    print("[PASS] 7. Grounded answer received with exact Page 2 citation!")
    
    # 8. Ask completely unrelated question
    question_2 = "What is the secret recipe for baking chocolate brownies with walnuts?"
    tutor_res2 = client.post(f"/projects/{proj_id}/tutor/chat", headers=alex_headers, json={
        "message": question_2
    })
    assert tutor_res2.status_code == 200
    ans2 = tutor_res2.json()
    print(f"\nQ: {question_2}")
    print(f"A: {ans2['answer']}")
    print(f"Sources: {ans2['sources']}")
    print(f"Grounded: {ans2['grounded']}")
    
    assert ans2["grounded"] is False
    assert len(ans2["sources"]) == 0
    assert "couldn't find enough information" in ans2["answer"].lower()
    print("[PASS] 8. Unsupported question politely declined without hallucinating!")
    
    # 9. Verify Conversation History
    history = client.get(f"/projects/{proj_id}/tutor/history", headers=alex_headers).json()
    assert len(history) == 4
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert history[2]["role"] == "user"
    assert history[3]["role"] == "assistant"
    print("[PASS] 9. Conversation history recorded and retrieved successfully")
    
    # 10. Verify Security Isolation: User Bob
    bob_reg = client.post("/auth/register", json={
        "name": "Bob Intruder",
        "email": "bob@intruder.edu",
        "password": "password123"
    })
    bob_token = bob_reg.json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}
    
    unauth_chat = client.post(f"/projects/{proj_id}/tutor/chat", headers=bob_headers, json={
        "message": "Give me Alex's notes"
    })
    assert unauth_chat.status_code == 404
    
    unauth_hist = client.get(f"/projects/{proj_id}/tutor/history", headers=bob_headers)
    assert unauth_hist.status_code == 404
    print("[PASS] 10. Security Isolation: Cross-user access to AI Tutor blocked with 404")

    print("\n=== ALL AI TUTOR & RAG E2E VERIFICATION CHECKS PASSED ===")

if __name__ == "__main__":
    run_tutor_e2e()
