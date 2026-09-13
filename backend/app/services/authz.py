import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.interview import Interview


def get_owned_document(db: Session, *, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    doc = db.get(Document, document_id)
    # Return 404 (not 403) on mismatch so we never confirm another user's resource exists.
    if doc is None or doc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


def get_owned_interview(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None or interview.user_id != user_id:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return interview
