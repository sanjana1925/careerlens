def test_register_creates_user(client):
    resp = client.post("/api/auth/register", json={
        "email": "new@example.com", "password": "s3cret-pass", "full_name": "New User",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["full_name"] == "New User"
    assert "hashed_password" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@example.com", "password": "s3cret-pass"}
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 400


def test_login_with_correct_credentials_returns_token(client):
    client.post("/api/auth/register", json={"email": "login@example.com", "password": "s3cret-pass"})

    resp = client.post("/api/auth/login", data={"username": "login@example.com", "password": "s3cret-pass"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "login2@example.com", "password": "s3cret-pass"})

    resp = client.post("/api/auth/login", data={"username": "login2@example.com", "password": "wrong-pass"})

    assert resp.status_code == 401


def test_login_unknown_email_rejected(client):
    resp = client.post("/api/auth/login", data={"username": "nobody@example.com", "password": "whatever"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_token(client):
    resp = client.get("/api/resumes")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_invalid_token(client):
    resp = client.get("/api/resumes", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
