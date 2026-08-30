import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make `app` importable regardless of how pytest computes its rootdir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Must be set before `app.config`/`app.database` are imported anywhere (including
# transitively, e.g. by `app.main`) — pydantic-settings reads these at import time.
# - GEMINI_API_KEY empty: forces every test through the deterministic
#   heuristic path (no live Gemini/Chroma calls, no quota spend, no flakiness).
# - JWT_SECRET_KEY: real value regardless of what's in the project's own .env.
# - DATABASE_URL: an isolated on-disk SQLite file, never the project's real
#   careerlens.db.
os.environ["GEMINI_API_KEY"] = ""
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key"
_TEST_DB_PATH = Path(tempfile.gettempdir()) / "careerlens_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"

if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    """Every test starts against empty tables — avoids order-dependent tests
    without needing per-test transactions (the app's own `get_db` opens/closes
    a real session per request, so a shared transaction would hide bugs that
    only show up across separate commits)."""
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    """Registers and logs in a fresh user, returns Authorization headers for it."""
    email = "testuser@example.com"
    password = "correct-horse-battery-staple"
    client.post("/api/auth/register", json={"email": email, "password": password})
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
