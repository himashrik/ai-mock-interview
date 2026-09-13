import uuid

from sqlalchemy.orm import Session

from app.core.prompts import RESUME_ANALYSIS_SYSTEM, JD_ANALYSIS_SYSTEM
from app.llm.factory import get_llm_provider
from app.schemas.document import ResumeAnalysis, JDAnalysis
from app.services.llm_json import call_llm_for_json
from app.services.vector_store import retrieve_relevant_chunks


def _default_resume_analysis() -> ResumeAnalysis:
    return ResumeAnalysis(missing_information=["Analysis unavailable — please retry shortly."])


def _default_jd_analysis() -> JDAnalysis:
    return JDAnalysis(target_role="Unknown — analysis unavailable, please retry shortly.")


def analyze_resume(db: Session, *, user_id: uuid.UUID, document_id: uuid.UUID) -> ResumeAnalysis:
    chunks = retrieve_relevant_chunks(
        db,
        user_id=user_id,
        query="skills education experience projects certifications achievements",
        document_types=["resume"],
        document_id=document_id,
        top_k=12,
    )
    if not chunks:
        return ResumeAnalysis(missing_information=["No resume content was found to analyze."])

    context = "\n---\n".join(c.content for c in chunks)
    llm = get_llm_provider()
    try:
        return call_llm_for_json(
            llm,
            ResumeAnalysis,
            RESUME_ANALYSIS_SYSTEM,
            f"Resume content chunks:\n{context}\n\nReturn the structured analysis JSON.",
        )
    except (ValueError, RuntimeError):
        return _default_resume_analysis()


def analyze_jd(db: Session, *, user_id: uuid.UUID, document_id: uuid.UUID) -> JDAnalysis:
    chunks = retrieve_relevant_chunks(
        db,
        user_id=user_id,
        query="role requirements responsibilities skills technologies experience",
        document_types=["jd"],
        document_id=document_id,
        top_k=12,
    )
    if not chunks:
        return JDAnalysis(target_role="No job description content was found to analyze.")

    context = "\n---\n".join(c.content for c in chunks)
    llm = get_llm_provider()
    try:
        return call_llm_for_json(
            llm,
            JDAnalysis,
            JD_ANALYSIS_SYSTEM,
            f"Job description content chunks:\n{context}\n\nReturn the structured analysis JSON.",
        )
    except (ValueError, RuntimeError):
        return _default_jd_analysis()
