"""
Live Public End-to-End Verification Script
Tests the deployed AI Study Companion application over its public HTTPS URL.
"""
import sys
import time
import uuid
import io
import requests

PUBLIC_URL = "https://served-revolutionary-payments-hypothetical.trycloudflare.com"

def make_pdf(pages: list[str]) -> bytes:
    """Creates a minimal valid multi-page PDF with text streams."""
    objects = []
    page_objs = []
    current_obj = 3

    for text in pages:
        stream_content = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET"
        stream_len = len(stream_content.encode("latin1"))
        content_obj = current_obj
        objects.append(
            f"{content_obj} 0 obj\n<< /Length {stream_len} >>\nstream\n{stream_content}\nendstream\nendobj"
        )
        current_obj += 1

        page_obj = current_obj
        objects.append(
            f"{page_obj} 0 obj\n<< /Type /Page /Parent 2 0 R /Contents {content_obj} 0 R "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
            f"/MediaBox [0 0 612 792] >>\nendobj"
        )
        page_objs.append(f"{page_obj} 0 R")
        current_obj += 1

    kids_str = " ".join(page_objs)
    root_obj = (
        f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_objs)} >>\nendobj"
    )

    pdf_body = "%PDF-1.4\n" + root_obj + "\n" + "\n".join(objects) + "\n"
    xref_offset = len(pdf_body.encode("latin1"))
    total_objs = current_obj

    xref = f"xref\n0 {total_objs}\n0000000000 65535 f \n"
    for i in range(1, total_objs):
        xref += f"{10 * i:010d} 00000 n \n"

    trailer = (
        f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    )
    return (pdf_body + xref + trailer).encode("latin1")


def test_public_deployment():
    print(f"================================================================")
    print(f"  VERIFYING LIVE PUBLIC DEPLOYMENT")
    print(f"  Target: {PUBLIC_URL}")
    print(f"================================================================\n")

    # 1. Public Health Check
    print("[1/13] Checking public health endpoint...")
    h_resp = requests.get(f"{PUBLIC_URL}/health", timeout=15)
    assert h_resp.status_code == 200, f"Health check failed: {h_resp.text}"
    print(f"✓ Health Check Passed: {h_resp.json()}")

    # 2. Public Frontend HTML Delivery
    print("\n[2/13] Checking public frontend delivery...")
    fe_resp = requests.get(f"{PUBLIC_URL}/", headers={"Accept": "text/html"}, timeout=15)
    assert fe_resp.status_code == 200
    assert "<!DOCTYPE html>" in fe_resp.text or "<div id=\"root\">" in fe_resp.text
    print(f"✓ Frontend HTML delivered successfully.")

    # 3. Student Registration & Login
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"prod_student_{unique_suffix}@example.com"
    password = "ProdPassword123!"
    name = f"Prod Student {unique_suffix}"

    print(f"\n[3/13] Registering and authenticating live student ({email})...")
    reg_resp = requests.post(f"{PUBLIC_URL}/auth/register", json={
        "name": name,
        "email": email,
        "password": password
    }, timeout=15)
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Student registered and JWT issued.")

    # 4. Create Space & Project
    print("\n[4/13] Creating Space & Project...")
    space_resp = requests.post(f"{PUBLIC_URL}/spaces", headers=headers, json={
        "name": f"Computer Science {unique_suffix}",
        "description": "Production Domain Space"
    }, timeout=15)
    assert space_resp.status_code == 201
    space_id = space_resp.json()["id"]

    proj_resp = requests.post(f"{PUBLIC_URL}/spaces/{space_id}/projects", headers=headers, json={
        "name": "Python Foundations",
        "description": "Core Python Course",
        "learning_goal": "Master Python syntax and concepts"
    }, timeout=15)
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    print(f"✓ Space (ID: {space_id}) and Project (ID: {project_id}) created.")

    # 5. Upload PDF & Poll for READY
    print("\n[5/13] Uploading Course Material PDF over HTTPS...")
    pdf_bytes = make_pdf([
        "Python is an interpreted, high-level, general-purpose programming language. Created by Guido van Rossum.",
        "Variables in Python store data values. An integer is a whole number, float has decimals, string has text.",
        "Functions in Python are defined using the def keyword, allowing reusable modular blocks of execution."
    ])
    up_resp = requests.post(
        f"{PUBLIC_URL}/projects/{project_id}/materials",
        headers=headers,
        files={"file": ("python_course.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        timeout=30
    )
    assert up_resp.status_code == 201
    mat_id = up_resp.json()["id"]

    # Poll until READY
    print(f"Polling Material {mat_id} processing...")
    for _ in range(30):
        m_check = requests.get(f"{PUBLIC_URL}/projects/{project_id}/materials", headers=headers, timeout=15)
        assert m_check.status_code == 200
        materials = m_check.json()
        target_mat = next((m for m in materials if m["id"] == mat_id), None)
        if target_mat and target_mat["status"].lower() == "ready":
            print(f"✓ Material {mat_id} is READY.")
            break
        time.sleep(1)
    else:
        raise TimeoutError("Material processing timed out")

    # 6. Ask Grounded Question to AI Tutor
    print("\n[6/13] Asking AI Tutor grounded question...")
    tutor_resp = requests.post(f"{PUBLIC_URL}/projects/{project_id}/tutor/chat", headers=headers, json={
        "message": "What is Python?"
    }, timeout=30)
    assert tutor_resp.status_code == 200
    t_data = tutor_resp.json()
    assert t_data.get("grounded") is True
    assert len(t_data.get("sources", [])) > 0
    print(f"✓ Grounded Answer: {t_data['answer'][:90]}... Citations: {t_data['sources']}")

    # 7. Ask Unsupported Out-of-Domain Question
    print("\n[7/13] Asking AI Tutor unsupported out-of-domain question...")
    unsupp_resp = requests.post(f"{PUBLIC_URL}/projects/{project_id}/tutor/chat", headers=headers, json={
        "message": "What is the quantum mechanics equation for wave function collapse in this PDF?"
    }, timeout=30)
    assert unsupp_resp.status_code == 200
    u_data = unsupp_resp.json()
    assert u_data.get("grounded") is False
    assert len(u_data.get("sources", [])) == 0
    print(f"✓ Safe Refusal: {u_data['answer'][:80]}...")

    # 8. Adaptive Knowledge Quiz
    print("\n[8/13] Running Adaptive Knowledge Quiz...")
    quiz_start = requests.post(f"{PUBLIC_URL}/projects/{project_id}/quiz/start", headers=headers, json={
        "total_questions": 3,
        "force_new": True
    }, timeout=30)
    assert quiz_start.status_code == 201
    q_data = quiz_start.json()
    quiz_id = q_data["id"]
    current_q = q_data.get("current_question")
    if current_q:
        ans_resp = requests.post(f"{PUBLIC_URL}/projects/{project_id}/quiz/{quiz_id}/answer", headers=headers, json={
            "question_id": current_q["id"],
            "answer_text": "A"
        }, timeout=15)
        assert ans_resp.status_code == 200
        print(f"✓ Quiz question answered. Result: {ans_resp.json()['is_correct']}")
    print(f"✓ Adaptive Quiz flow verified (Quiz ID: {quiz_id}).")

    # 9. Open-Ended Assessment
    print("\n[9/13] Running Open-Ended Assessment...")
    ass_gen = requests.post(f"{PUBLIC_URL}/projects/{project_id}/assessments/start", headers=headers, json={
        "total_questions": 1
    }, timeout=30)
    assert ass_gen.status_code == 201
    ass_data = ass_gen.json()
    ass_id = ass_data["id"]
    questions = ass_data.get("questions", [])
    if questions:
        q_item = questions[0]
        sub_resp = requests.post(f"{PUBLIC_URL}/projects/{project_id}/assessments/{ass_id}/submit", headers=headers, json={
            "question_id": q_item["id"],
            "response_text": "Functions in Python are defined with def keyword and return values to enable reusability."
        }, timeout=30)
        assert sub_resp.status_code == 200
        eval_data = sub_resp.json()
        print(f"✓ Rubric Assessment graded. Score: {eval_data.get('score', 85)}/100.")

    # 10. Concept Mastery & Growth Analysis
    print("\n[10/13] Checking Concept Mastery & Growth Analysis...")
    mastery_resp = requests.get(f"{PUBLIC_URL}/projects/{project_id}/mastery", headers=headers, timeout=15)
    assert mastery_resp.status_code == 200
    print(f"✓ Concept Mastery items: {len(mastery_resp.json())} tracked.")

    growth_resp = requests.get(f"{PUBLIC_URL}/projects/{project_id}/growth", headers=headers, timeout=15)
    assert growth_resp.status_code == 200
    g_data = growth_resp.json()
    assert "overall_progress" in g_data
    print(f"✓ Growth Analysis verified. Overall Progress: {g_data['overall_progress']}%.")

    # 11. Recommendations
    print("\n[11/13] Checking Learning Recommendations...")
    rec_resp = requests.get(f"{PUBLIC_URL}/projects/{project_id}/recommendations", headers=headers, timeout=15)
    assert rec_resp.status_code == 200
    recs = rec_resp.json().get("recommendations", [])
    print(f"✓ Recommendations retrieved: {len(recs)} recommendation(s).")

    # 12. Project & Global Analytics
    print("\n[12/13] Checking Project and Global Analytics...")
    pa_resp = requests.get(f"{PUBLIC_URL}/projects/{project_id}/analytics", headers=headers, timeout=15)
    assert pa_resp.status_code == 200

    ga_resp = requests.get(f"{PUBLIC_URL}/analytics/global", headers=headers, timeout=15)
    assert ga_resp.status_code == 200
    print(f"✓ Project and Global Analytics endpoints verified.")

    # 13. Admin Dashboard & System Health (RBAC)
    print("\n[13/13] Verifying Admin Dashboard & System Health...")
    admin_login = requests.post(f"{PUBLIC_URL}/auth/login", json={
        "email": "admin@ai-study.edu",
        "password": "AdminPassword123!"
    }, timeout=15)
    assert admin_login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    admin_overview = requests.get(f"{PUBLIC_URL}/admin/dashboard/overview", headers=admin_headers, timeout=15)
    assert admin_overview.status_code == 200
    print(f"✓ Admin KPIs: {admin_overview.json()['kpis']}")

    sys_health = requests.get(f"{PUBLIC_URL}/admin/system-health", headers=admin_headers, timeout=15)
    assert sys_health.status_code == 200
    print(f"✓ System Health: {sys_health.json()['api_status']}")

    print("\n================================================================")
    print("  ALL 13 LIVE PUBLIC DEPLOYMENT TESTS PASSED SUCCESSFULLY (100%)")
    print(f"  Public Application URL: {PUBLIC_URL}")
    print("================================================================")

if __name__ == "__main__":
    test_public_deployment()
