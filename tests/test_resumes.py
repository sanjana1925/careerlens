import io


def _upload_txt_resume(client, auth_headers, text="Experienced Python and FastAPI developer."):
    return client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.txt", io.BytesIO(text.encode()), "text/plain")},
    )


def test_upload_resume_extracts_and_stores_text(client, auth_headers):
    resp = _upload_txt_resume(client, auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "resume.txt"
    assert "id" in body


def test_upload_resume_rejects_unsupported_extension(client, auth_headers):
    resp = client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.exe", io.BytesIO(b"not a resume"), "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_upload_resume_rejects_file_exceeding_size_cap(client, auth_headers):
    from app.services.resume_parser import MAX_UPLOAD_BYTES

    oversized = b"a" * (MAX_UPLOAD_BYTES + 1)
    resp = client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.txt", io.BytesIO(oversized), "text/plain")},
    )
    assert resp.status_code == 413


def test_upload_resume_rejects_pdf_with_mismatched_content(client, auth_headers):
    resp = client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.pdf", io.BytesIO(b"this is not actually a pdf"), "application/pdf")},
    )
    assert resp.status_code == 400


def test_upload_resume_rejects_docx_with_mismatched_content(client, auth_headers):
    resp = client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.docx", io.BytesIO(b"this is not actually a docx"), "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_list_resumes_supports_pagination(client, auth_headers):
    for i in range(3):
        _upload_txt_resume(client, auth_headers, text=f"Resume {i}")

    page = client.get("/api/resumes", params={"limit": 1, "offset": 1}, headers=auth_headers)
    assert page.status_code == 200
    assert len(page.json()) == 1


def test_list_resumes_only_returns_current_users_resumes(client):
    client.post("/api/auth/register", json={"email": "a@example.com", "password": "s3cret-pass"})
    token_a = client.post("/api/auth/login", data={"username": "a@example.com", "password": "s3cret-pass"}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    client.post("/api/auth/register", json={"email": "b@example.com", "password": "s3cret-pass"})
    token_b = client.post("/api/auth/login", data={"username": "b@example.com", "password": "s3cret-pass"}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    _upload_txt_resume(client, headers_a)

    assert len(client.get("/api/resumes", headers=headers_a).json()) == 1
    assert len(client.get("/api/resumes", headers=headers_b).json()) == 0


def test_analyze_resume_returns_deterministic_score_and_heuristic_narrative(client, auth_headers):
    upload = _upload_txt_resume(client, auth_headers, "Python, FastAPI, and Docker developer.")
    resume_id = upload.json()["id"]

    resp = client.post("/api/resumes/analyze", headers=auth_headers, json={"resume_id": resume_id})

    assert resp.status_code == 200
    body = resp.json()
    assert "python" in body["matched_keywords"]
    assert 0.0 <= body["ats_score"] <= 100.0
    assert body["strengths"]


def test_analyze_resume_not_found_returns_404(client, auth_headers):
    resp = client.post("/api/resumes/analyze", headers=auth_headers, json={"resume_id": 999999})
    assert resp.status_code == 404


def test_analyze_resume_belonging_to_another_user_returns_404(client, auth_headers):
    client.post("/api/auth/register", json={"email": "other@example.com", "password": "s3cret-pass"})
    other_token = client.post("/api/auth/login", data={"username": "other@example.com", "password": "s3cret-pass"}).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    upload = _upload_txt_resume(client, other_headers)
    resume_id = upload.json()["id"]

    resp = client.post("/api/resumes/analyze", headers=auth_headers, json={"resume_id": resume_id})
    assert resp.status_code == 404


def test_list_analyses_returns_saved_runs_most_recent_first(client, auth_headers):
    upload = _upload_txt_resume(client, auth_headers)
    resume_id = upload.json()["id"]

    client.post("/api/resumes/analyze", headers=auth_headers, json={"resume_id": resume_id})
    client.post("/api/resumes/analyze", headers=auth_headers, json={"resume_id": resume_id})

    resp = client.get(f"/api/resumes/{resume_id}/analyses", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_analyze_projects_manual_submission(client, auth_headers):
    upload = _upload_txt_resume(client, auth_headers)
    resume_id = upload.json()["id"]

    resp = client.post(
        "/api/resumes/projects/analyze",
        headers=auth_headers,
        json={
            "resume_id": resume_id,
            "projects": [
                {"title": "House Prices", "description": "A regression model predicting house prices."},
                {"title": "Student Grades", "description": "A classifier predicting student grades."},
            ],
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["projects"]) == 2
    assert any(p["is_repetitive"] for p in body["projects"])


def test_auto_analyze_projects_without_projects_section_returns_400(client, auth_headers):
    upload = _upload_txt_resume(client, auth_headers, "Just a plain resume with no projects section at all.")
    resume_id = upload.json()["id"]

    resp = client.post("/api/resumes/projects/auto-analyze", headers=auth_headers, json={"resume_id": resume_id})
    assert resp.status_code == 400
