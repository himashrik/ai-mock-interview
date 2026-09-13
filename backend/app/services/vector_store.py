import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.rag.chunking import chunk_text, clean_text
from app.services.embeddings import get_embedding_provider


def index_document(db: Session, *, user_id: uuid.UUID, document_id: uuid.UUID, document_type: str, raw_text: str) -> int:
    """Clean, chunk, embed, and store a document's chunks. Returns number of chunks stored."""
    cleaned = clean_text(raw_text)
    pieces = chunk_text(cleaned)
    if not pieces:
        return 0

    provider = get_embedding_provider()
    vectors = provider.embed(pieces)

    for idx, (content, vector) in enumerate(zip(pieces, vectors)):
        db.add(
            DocumentChunk(
                document_id=document_id,
                user_id=user_id,
                document_type=document_type,
                chunk_index=idx,
                content=content,
                embedding=vector,
                chunk_metadata={"section_hint": None},
            )
        )
    db.commit()
    return len(pieces)


def retrieve_relevant_chunks(
    db: Session,
    *,
    user_id: uuid.UUID,
    query: str,
    document_types: list[str] | None = None,
    document_id: uuid.UUID | None = None,
    top_k: int = 5,
) -> list[DocumentChunk]:
    """Retrieve the top_k most relevant chunks for `query`, scoped strictly to `user_id`.

    This is the isolation boundary: the WHERE clause on user_id is enforced in SQL,
    so one user's private data can never be retrieved for another user regardless
    of what the application layer does upstream.
    """
    provider = get_embedding_provider()
    query_vector = provider.embed_one(query)

    stmt = select(DocumentChunk).where(DocumentChunk.user_id == user_id)
    if document_types:
        stmt = stmt.where(DocumentChunk.document_type.in_(document_types))
    if document_id:
        stmt = stmt.where(DocumentChunk.document_id == document_id)

    stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_vector)).limit(top_k)
    return list(db.execute(stmt).scalars().all())
