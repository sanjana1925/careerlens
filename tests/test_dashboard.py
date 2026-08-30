import io


def test_dashboard_summary_empty_state(client, auth_headers):
    resp = client.get("/api/dashboard/summary", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["resume_count"] == 0
    assert body["ats_resume_score"] is None
    assert body["profile_strength"] == 0.0
    assert "Upload your resume" in body["recommended_actions"][0]


def test_dashboard_summary_reflects_uploaded_resume_and_analysis(client, auth_headers):
    upload = client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.txt", io.BytesIO(b"Python and Docker developer."), "text/plain")},
    )
    resume_id = upload.json()["id"]
    client.post("/api/resumes/analyze", headers=auth_headers, json={"resume_id": resume_id})

    resp = client.get("/api/dashboard/summary", headers=auth_headers)

    body = resp.json()
    assert body["resume_count"] == 1
    assert body["ats_resume_score"] is not None
    assert body["profile_strength"] == 50.0  # resume uploaded + analysis run = 2 * 25
