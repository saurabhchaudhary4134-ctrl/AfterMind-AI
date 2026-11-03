"""Shared pytest fixtures: test database, client, helpers."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# Ensure test settings are used before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_aftermind.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("SIMULATION_SYNC", "true")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
# Reset LLM provider so tests that don't set it explicitly get no-LLM behaviour
os.environ.setdefault("LLM_PROVIDER", "")

from app.db.base import Base  # noqa: E402
from app.models import *  # noqa: E402, F401, F403

# ── Test database ─────────────────────────────────────────────

_test_db_path = os.path.join(tempfile.gettempdir(), "aftermind_test.db")
_test_db_url = f"sqlite:///{_test_db_path}"

test_engine = create_engine(
    _test_db_url,
    connect_args={"check_same_thread": False},
)


@event.listens_for(test_engine, "connect")
def _enable_fk(dbapi_conn, _record):  # pragma: no cover
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Yield a fresh DB session with a clean schema for each test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Yield a FastAPI TestClient wired to the test database.

    The rate-limiter windows are cleared before each test so tests that
    exercise rate limiting don't bleed into unrelated tests.
    """
    from app.db import session as session_module
    from app.core.rate_limit import limiter

    # Clear all rate-limiter state before each test
    with limiter._lock:
        limiter._windows.clear()

    # Patch the session to use the test engine
    original_session_local = session_module.SessionLocal
    session_module.SessionLocal = TestSessionLocal

    from app.main import app

    def _get_test_db():
        s = TestSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[session_module.get_db] = _get_test_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    session_module.SessionLocal = original_session_local


# ── Helpers ──────────────────────────────────────────────────

def register_and_login(client: TestClient, email: str = "alice@test.com",
                        password: str = "Test1234!", name: str = "Alice") -> dict:
    """Register a user and return auth headers."""
    resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": name,
    })
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
