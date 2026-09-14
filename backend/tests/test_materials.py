import io

def test_material_upload_non_pdf_rejected(client, user_a_headers):
    # Setup space & project
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Science"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Physics"}).json()

    # Attempt to upload .txt file
    files = {"file": ("notes.txt", io.BytesIO(b"Hello world text file"), "text/plain")}
    res = client.post(f"/projects/{proj['id']}/materials", headers=user_a_headers, files=files)
    assert res.status_code == 400
    assert "pdf" in res.json()["detail"].lower()

    # Attempt to upload fake pdf with invalid magic bytes
    fake_pdf = {"file": ("fake.pdf", io.BytesIO(b"Not a real pdf content"), "application/pdf")}
    res2 = client.post(f"/projects/{proj['id']}/materials", headers=user_a_headers, files=fake_pdf)
    assert res2.status_code == 400
    assert "not a valid pdf" in res2.json()["detail"].lower()

def test_material_upload_valid_pdf(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Math"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Linear Algebra"}).json()

    # Valid PDF with %PDF- header
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    files = {"file": ("algebra_chapter1.pdf", io.BytesIO(pdf_content), "application/pdf")}

    res = client.post(f"/projects/{proj['id']}/materials", headers=user_a_headers, files=files)
    assert res.status_code == 201
    mat = res.json()
    assert mat["filename"] == "algebra_chapter1.pdf"
    assert mat["status"] in ["queued", "processing", "ready"]
    mat_id = mat["id"]

    # List materials
    list_res = client.get(f"/projects/{proj['id']}/materials", headers=user_a_headers)
    assert list_res.status_code == 200
    materials = list_res.json()
    assert any(m["id"] == mat_id for m in materials)

    # Get single material
    single_res = client.get(f"/materials/{mat_id}", headers=user_a_headers)
    assert single_res.status_code == 200
    assert single_res.json()["filename"] == "algebra_chapter1.pdf"

def test_material_isolation_between_users(client, user_a_headers, user_b_headers):
    space_a = client.post("/spaces", headers=user_a_headers, json={"name": "A Space"}).json()
    proj_a = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={"name": "A Project"}).json()

    # User B tries to upload material to User A's project -> 404
    pdf_content = b"%PDF-1.4\nsome pdf\n%%EOF"
    files = {"file": ("intruder.pdf", io.BytesIO(pdf_content), "application/pdf")}
    res = client.post(f"/projects/{proj_a['id']}/materials", headers=user_b_headers, files=files)
    assert res.status_code == 404

    # User A uploads a material
    res_a = client.post(f"/projects/{proj_a['id']}/materials", headers=user_a_headers, files=files)
    assert res_a.status_code == 201
    mat_a_id = res_a.json()["id"]

    # User B tries to list User A's project materials -> 404
    assert client.get(f"/projects/{proj_a['id']}/materials", headers=user_b_headers).status_code == 404

    # User B tries to view User A's material directly -> 404
    assert client.get(f"/materials/{mat_a_id}", headers=user_b_headers).status_code == 404
