import json
import uuid
from typing import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.main import app

# Import models so their tables are registered on Base.metadata.
from app.models import user, document, interview, assistant, revoked_token  # noqa: F401


class FakeLLMProvider:
    """A drop-in LLMProvider that returns pre-programmed responses instead of calling a real API.

    Tests configure `.json_responses` (a list consumed in order) and/or `.text_response`.
    """

    def __init__(self, json_responses: list[str] | None = None, text_response: str = "Great job overall."):
        self.json_responses = list(json_responses or [])
        self.text_response = text_response
        self.calls = []

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
        self.calls.append(("json", system_prompt, user_prompt))
        if not self.json_responses:
            return "{}"
        return self.json_responses.pop(0)

    def complete_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
        self.calls.append(("text", system_prompt, user_prompt))
        return self.text_response


@pytest.fixture
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def patch_llm_provider(monkeypatch, fake_llm) -> Callable:
    """Patches get_llm_provider in every module that imported it by name, so
    services under test receive `fake_llm` instead of a real Anthropic/OpenAI client."""

    def _apply(*module_paths: str):
        for path in module_paths:
            monkeypatch.setattr(f"{path}.get_llm_provider", lambda: fake_llm)
        return fake_llm

    return _apply


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The rate limiter is a module-level singleton shared across the whole test process, and
    TestClient always uses the same fake client IP ("testclient"), so without a reset every test
    file would accumulate hits against the same bucket and eventually 429 unrelated tests."""
    from app.core.limiter import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def sqlite_engine():
    """An in-memory SQLite engine with all tables EXCEPT document_chunks, which uses the
    Postgres-only pgvector type and is out of scope for these fast unit/integration tests.
    Vector-store behavior is covered separately by tests requiring a real Postgres+pgvector
    instance (see test_vector_store.py, skipped automatically if unavailable)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # all connections share the same in-memory DB (required for :memory:)
    )
    tables = [t for name, t in Base.metadata.tables.items() if name != "document_chunks"]
    Base.metadata.create_all(bind=engine, tables=tables)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    """Registers and logs in a user, returning (user_dict, auth_headers)."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "correct-horse-battery-staple"

    resp = client.post("/auth/register", json={"email": email, "password": password, "full_name": "Test User"})
    assert resp.status_code == 201, resp.text

    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    tokens = resp.json()

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return resp.json(), headers, email, password
