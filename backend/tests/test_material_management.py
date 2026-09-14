import io
import os
import time
from fpdf import FPDF
from app.models.document_chunk import DocumentChunk
from app.models.material import Material
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

def test_delete_material_removes_file_and_chunks(client, db_session, user_a_headers):
    # Setup space & project
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Science Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Biology"}).json()

    # Upload material
    pdf_bytes = make_sample_pdf([
        "Cell theory states that all living organisms are composed of cells and come from preexisting cells.",
        "Mitochondria generate most of the chemical energy needed to power the cell's biochemical reactions."
    ])
    files = {"file": ("biology_ch1.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj['id']}/materials", headers=user_a_headers, files=files)
    assert upload_res.status_code == 201
    mat_id = upload_res.json()["id"]

    # Wait for ready
    mat_data = poll_for_ready(client, user_a_headers, mat_id)
    assert mat_data["status"] == "ready"

    # Verify physical file exists
    mat_obj = db_session.query(Material).filter(Material.id == mat_id).first()
    assert mat_obj is not None
    assert os.path.exists(mat_obj.file_path)

    # Verify chunks exist
    chunks_before = db_session.query(DocumentChunk).filter(DocumentChunk.material_id == mat_id).all()
    assert len(chunks_before) > 0

    # Delete material
    del_res = client.delete(f"/projects/{proj['id']}/materials/{mat_id}", headers=user_a_headers)
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]

    # Verify physical file removed
    assert not os.path.exists(mat_obj.file_path)

    # Verify chunks removed
    chunks_after = db_session.query(DocumentChunk).filter(DocumentChunk.material_id == mat_id).all()
    assert len(chunks_after) == 0

    # Verify material record removed
    mat_after = db_session.query(Material).filter(Material.id == mat_id).first()
    assert mat_after is None

    # Verify MATERIAL_DELETED activity event logged
    event = (
        db_session.query(ActivityEvent)
        .filter(ActivityEvent.event_type == ActivityEventType.MATERIAL_DELETED.value)
        .order_by(ActivityEvent.created_at.desc())
        .first()
    )
    assert event is not None
    assert event.metadata_json["material_id"] == mat_id

def test_replace_material_invalidates_old_chunks(client, db_session, user_a_headers):
    # Setup project
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Physics Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Mechanics"}).json()

    # 1. Upload initial PDF about Classical Mechanics
    pdf_a = make_sample_pdf([
        "Classical mechanics describes the motion of macroscopic objects from projectiles to parts of machinery."
    ])
    files_a = {"file": ("classical_mechanics.pdf", io.BytesIO(pdf_a), "application/pdf")}
    upload_res = client.post(f"/projects/{proj['id']}/materials", headers=user_a_headers, files=files_a)
    mat_id = upload_res.json()["id"]

    poll_for_ready(client, user_a_headers, mat_id)

    # Verify tutor answers about classical mechanics
    chat_a = client.post(f"/projects/{proj['id']}/tutor/chat", headers=user_a_headers, json={"message": "What does classical mechanics describe?"})
    assert chat_a.status_code == 200
    assert chat_a.json()["grounded"] is True
    assert "macroscopic" in chat_a.json()["answer"].lower()

    # 2. Replace with PDF B about Thermodynamics
    pdf_b = make_sample_pdf([
        "Thermodynamics is the branch of physics that deals with heat, work, and temperature, and their relation to energy."
    ])
    files_b = {"file": ("thermodynamics.pdf", io.BytesIO(pdf_b), "application/pdf")}
    replace_res = client.put(f"/projects/{proj['id']}/materials/{mat_id}/replace", headers=user_a_headers, files=files_b)
    assert replace_res.status_code == 200
    assert replace_res.json()["filename"] == "thermodynamics.pdf"

    # Wait for processing
    poll_for_ready(client, user_a_headers, mat_id)

    # 3. Tutor should now answer about thermodynamics
    chat_b = client.post(f"/projects/{proj['id']}/tutor/chat", headers=user_a_headers, json={"message": "What is thermodynamics?"})
    assert chat_b.status_code == 200
    assert chat_b.json()["grounded"] is True
    assert "heat" in chat_b.json()["answer"].lower()

    # 4. Old classical mechanics content should NO LONGER be answerable
    chat_stale = client.post(f"/projects/{proj['id']}/tutor/chat", headers=user_a_headers, json={"message": "What does classical mechanics describe?"})
    assert chat_stale.status_code == 200
    assert chat_stale.json()["grounded"] is False
    assert "couldn't find" in chat_stale.json()["answer"].lower()

    # Verify MATERIAL_REPLACED activity event
    event = (
        db_session.query(ActivityEvent)
        .filter(ActivityEvent.event_type == ActivityEventType.MATERIAL_REPLACED.value)
        .order_by(ActivityEvent.created_at.desc())
        .first()
    )
    assert event is not None
    assert event.metadata_json["material_id"] == mat_id

def test_material_delete_replace_isolation(client, user_a_headers, user_b_headers):
    space_a = client.post("/spaces", headers=user_a_headers, json={"name": "Private Space"}).json()
    proj_a = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={"name": "Secret Project"}).json()

    pdf_bytes = make_sample_pdf(["Secret information text only for User A."])
    files = {"file": ("secret.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj_a['id']}/materials", headers=user_a_headers, files=files)
    mat_id = upload_res.json()["id"]

    # User B attempts to delete User A's material -> 404
    del_res = client.delete(f"/projects/{proj_a['id']}/materials/{mat_id}", headers=user_b_headers)
    assert del_res.status_code == 404

    # User B attempts to replace User A's material -> 404
    rep_files = {"file": ("hacked.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    rep_res = client.put(f"/projects/{proj_a['id']}/materials/{mat_id}/replace", headers=user_b_headers, files=rep_files)
    assert rep_res.status_code == 404
