"""These tests exercise the real pgvector-backed vector store and therefore require a live
PostgreSQL instance with the `vector` extension available. Set TEST_DATABASE_URL to run them,
e.g.:

    docker run -d -p 5433:5432 -e POSTGRES_PASSWORD=postgres ankane/pgvector
    TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5433/postgres pytest tests/test_vector_store.py

They are automatically skipped in environments without that variable set (e.g. this sandbox),
so they never fail the default `pytest` run for contributors without Docker handy.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set; skipping real-Postgres/pgvector integration tests"
)


@pytest.fixture
def pg_session():
    from app.db.base import Base
    from app.models import assistant, document, interview, revoked_token, user  # noqa: F401

    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_index_and_retrieve_respects_user_isolation(pg_session, monkeypatch):
    from app.core.config import settings
    from app.core.security import hash_password
    from app.models.document import Document
    from app.models.user import User
    from app.services import vector_store

    # Use a tiny deterministic fake embedding provider instead of downloading a real model.
    # Vectors must match the real column width (settings.embedding_dim, baked into the
    # DocumentChunk model at import time) since embedding_dim is a read-only computed property
    # and the actual `vector(N)` column type can't be changed per-test.
    dim = settings.embedding_dim

    class FakeEmbeddingProvider:
        def embed(self, texts):
            return [[float(len(t) % 7)] + [0.0] * (dim - 1) for t in texts]

        def embed_one(self, text):
            return self.embed([text])[0]

    monkeypatch.setattr(vector_store, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    # Real Postgres enforces the documents.user_id -> users.id foreign key (unlike SQLite by
    # default), so real User rows are required here, not just arbitrary UUIDs.
    user_a = User(email="alice@example.com", hashed_password=hash_password("password123"), full_name="Alice")
    user_b = User(email="bob@example.com", hashed_password=hash_password("password123"), full_name="Bob")
    pg_session.add_all([user_a, user_b])
    pg_session.commit()

    doc_a = Document(user_id=user_a.id, type="resume", filename="a.pdf", raw_text="", status="ready")
    doc_b = Document(user_id=user_b.id, type="resume", filename="b.pdf", raw_text="", status="ready")
    pg_session.add_all([doc_a, doc_b])
    pg_session.commit()

    vector_store.index_document(
        pg_session, user_id=user_a.id, document_id=doc_a.id, document_type="resume",
        raw_text="Alice is a backend engineer skilled in Python and distributed systems.",
    )
    vector_store.index_document(
        pg_session, user_id=user_b.id, document_id=doc_b.id, document_type="resume",
        raw_text="Bob is a frontend engineer skilled in React and CSS.",
    )

    results_for_a = vector_store.retrieve_relevant_chunks(
        pg_session, user_id=user_a.id, query="Python backend", document_types=["resume"], top_k=5
    )
    assert all(c.user_id == user_a.id for c in results_for_a)
    assert not any("Bob" in c.content for c in results_for_a)
