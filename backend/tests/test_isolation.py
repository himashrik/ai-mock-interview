import uuid

import pytest
from fastapi import HTTPException

from app.models.document import Document
from app.models.interview import Interview
from app.services.authz import get_owned_document, get_owned_interview


def _make_document(db_session, user_id, doc_type="resume"):
    doc = Document(user_id=user_id, type=doc_type, filename="resume.pdf", raw_text="text", status="ready")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def _make_interview(db_session, user_id):
    interview = Interview(
        user_id=user_id, type="technical", target_role="Backend Engineer",
        experience_level="junior", difficulty="medium", mode="general", num_questions=5,
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)
    return interview


def test_owner_can_access_their_own_document(db_session):
    user_id = uuid.uuid4()
    doc = _make_document(db_session, user_id)
    fetched = get_owned_document(db_session, user_id=user_id, document_id=doc.id)
    assert fetched.id == doc.id


def test_other_user_gets_404_not_403_for_someone_elses_document(db_session):
    owner_id = uuid.uuid4()
    attacker_id = uuid.uuid4()
    doc = _make_document(db_session, owner_id)

    with pytest.raises(HTTPException) as exc:
        get_owned_document(db_session, user_id=attacker_id, document_id=doc.id)

    # 404, not 403 -- we never confirm to an attacker that the resource exists.
    assert exc.value.status_code == 404


def test_nonexistent_document_id_also_gets_404(db_session):
    with pytest.raises(HTTPException) as exc:
        get_owned_document(db_session, user_id=uuid.uuid4(), document_id=uuid.uuid4())
    assert exc.value.status_code == 404


def test_other_user_gets_404_for_someone_elses_interview(db_session):
    owner_id = uuid.uuid4()
    attacker_id = uuid.uuid4()
    interview = _make_interview(db_session, owner_id)

    with pytest.raises(HTTPException) as exc:
        get_owned_interview(db_session, user_id=attacker_id, interview_id=interview.id)
    assert exc.value.status_code == 404


def test_owner_can_access_their_own_interview(db_session):
    user_id = uuid.uuid4()
    interview = _make_interview(db_session, user_id)
    fetched = get_owned_interview(db_session, user_id=user_id, interview_id=interview.id)
    assert fetched.id == interview.id


class TestApiLevelIsolation:
    """End-to-end: two real registered users, verifying cross-access is blocked at the API layer."""

    def test_user_b_cannot_fetch_user_as_resume_via_api(self, client):
        # User A registers and creates a document directly (bypassing upload/RAG indexing,
        # which requires Postgres+pgvector) to isolate the authorization behavior under test.
        resp_a = client.post("/auth/register", json={"email": "a@example.com", "password": "password123", "full_name": "A"})
        assert resp_a.status_code == 201
        user_a_id = resp_a.json()["id"]

        resp_b = client.post("/auth/register", json={"email": "b@example.com", "password": "password123", "full_name": "B"})
        assert resp_b.status_code == 201
        login_b = client.post("/auth/login", json={"email": "b@example.com", "password": "password123"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        from app.db.base import get_db
        from app.main import app as fastapi_app

        # Grab the overridden test session to insert a document owned by user A.
        db_session = next(fastapi_app.dependency_overrides[get_db]())
        doc = Document(user_id=uuid.UUID(user_a_id), type="resume", filename="a_resume.pdf", raw_text="secret", status="ready")
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        resp = client.get(f"/resumes/{doc.id}", headers=headers_b)
        assert resp.status_code == 404

    def test_unauthenticated_request_to_protected_route_is_401(self, client):
        resp = client.get(f"/resumes/{uuid.uuid4()}")
        assert resp.status_code == 401
