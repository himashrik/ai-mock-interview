import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.prompts import ASSISTANT_SYSTEM
from app.llm.factory import get_llm_provider
from app.models.assistant import AssistantMessage
from app.models.document import Document
from app.services.vector_store import retrieve_relevant_chunks

HISTORY_TURNS = 10  # how many prior messages to include as conversational context
FALLBACK_REPLY = (
    "I'm having trouble reaching the assistant service right now. Please try again in a moment -- "
    "in the meantime, the Resume, Job Description, and Interview Report pages have detailed, "
    "always-available feedback you can act on."
)


def _latest_ready_document_id(db: Session, *, user_id: uuid.UUID, doc_type: str) -> uuid.UUID | None:
    doc = (
        db.execute(
            select(Document)
            .where(Document.user_id == user_id, Document.type == doc_type, Document.status == "ready")
            .order_by(Document.created_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    return doc.id if doc else None


def _grounding_context(db: Session, *, user_id: uuid.UUID, query: str) -> str:
    resume_id = _latest_ready_document_id(db, user_id=user_id, doc_type="resume")
    jd_id = _latest_ready_document_id(db, user_id=user_id, doc_type="jd")

    if not resume_id and not jd_id:
        return "(no resume or job description on file for this user)"

    parts = []
    if resume_id:
        chunks = retrieve_relevant_chunks(
            db, user_id=user_id, query=query, document_types=["resume"], document_id=resume_id, top_k=4
        )
        if chunks:
            parts.append("RESUME EXCERPTS:\n" + "\n---\n".join(c.content for c in chunks))
    if jd_id:
        chunks = retrieve_relevant_chunks(
            db, user_id=user_id, query=query, document_types=["jd"], document_id=jd_id, top_k=4
        )
        if chunks:
            parts.append("JOB DESCRIPTION EXCERPTS:\n" + "\n---\n".join(c.content for c in chunks))

    return "\n\n".join(parts) if parts else "(resume/JD on file, but no relevant excerpts found for this question)"


def get_history(db: Session, *, user_id: uuid.UUID) -> list[AssistantMessage]:
    return list(
        db.execute(
            select(AssistantMessage).where(AssistantMessage.user_id == user_id).order_by(AssistantMessage.created_at)
        )
        .scalars()
        .all()
    )


def send_message(db: Session, *, user_id: uuid.UUID, message: str) -> AssistantMessage:
    user_message = AssistantMessage(user_id=user_id, role="user", content=message)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    history = get_history(db, user_id=user_id)
    recent = history[-(HISTORY_TURNS + 1) : -1]  # exclude the message we just added, cap length
    history_text = "\n".join(f"{m.role}: {m.content}" for m in recent) or "(no prior messages)"

    context = _grounding_context(db, user_id=user_id, query=message)

    user_prompt = (
        f"Conversation so far:\n{history_text}\n\n"
        f"Context available for this user:\n{context}\n\n"
        f"User's new message: {message}\n\n"
        "Respond as the assistant."
    )

    llm = get_llm_provider()
    try:
        reply_text = llm.complete_text(ASSISTANT_SYSTEM, user_prompt, max_tokens=700)
        if not reply_text.strip():
            raise ValueError("empty response")
    except Exception:  # noqa: BLE001 - never let a chat-assistant hiccup break the request
        reply_text = FALLBACK_REPLY

    assistant_message = AssistantMessage(user_id=user_id, role="assistant", content=reply_text)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    return assistant_message
