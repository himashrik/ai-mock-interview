import uuid

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.prompts import ATS_ANALYSIS_SYSTEM
from app.llm.factory import get_llm_provider
from app.services.llm_json import call_llm_for_json
from app.services.vector_store import retrieve_relevant_chunks


class AtsAnalysisResult(BaseModel):
    score: float = Field(ge=0, le=100)
    matching_keywords: list[str] = []
    missing_keywords: list[str] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []


class AtsAnalysisUnavailable(Exception):
    """Raised when a real ATS analysis cannot be produced (never falls back to a fake score)."""


def run_ats_analysis(
    db: Session, *, user_id: uuid.UUID, resume_document_id: uuid.UUID, jd_document_id: uuid.UUID
) -> AtsAnalysisResult:
    resume_chunks = retrieve_relevant_chunks(
        db, user_id=user_id, query="skills experience projects education", document_types=["resume"],
        document_id=resume_document_id, top_k=15,
    )
    jd_chunks = retrieve_relevant_chunks(
        db, user_id=user_id, query="required skills responsibilities qualifications", document_types=["jd"],
        document_id=jd_document_id, top_k=15,
    )

    if not resume_chunks or not jd_chunks:
        raise AtsAnalysisUnavailable(
            "Both a processed resume and a processed job description are required for ATS analysis."
        )

    resume_context = "\n---\n".join(c.content for c in resume_chunks)
    jd_context = "\n---\n".join(c.content for c in jd_chunks)

    llm = get_llm_provider()
    try:
        return call_llm_for_json(
            llm,
            AtsAnalysisResult,
            ATS_ANALYSIS_SYSTEM,
            f"RESUME CONTENT:\n{resume_context}\n\nJOB DESCRIPTION CONTENT:\n{jd_context}\n\n"
            "Return the ATS analysis JSON.",
            max_tokens=2000,
        )
    except (ValueError, RuntimeError) as e:
        raise AtsAnalysisUnavailable(f"ATS analysis could not be completed: {e}")
