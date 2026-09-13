from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.prompts import EVALUATOR_SYSTEM
from app.llm.factory import get_llm_provider
from app.models.document import DocumentChunk
from app.models.interview import Answer, Feedback, Interview, Question
from app.services.llm_json import call_llm_for_json
from app.services.scoring import question_score


class EvaluationResult(BaseModel):
    correctness: float = Field(ge=0, le=100)
    relevance: float = Field(ge=0, le=100)
    technical_accuracy: float = Field(ge=0, le=100)
    completeness: float = Field(ge=0, le=100)
    communication: float = Field(ge=0, le=100)
    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []
    sample_answer: str = ""


def _fallback_evaluation() -> EvaluationResult:
    return EvaluationResult(
        correctness=50, relevance=50, technical_accuracy=0, completeness=50, communication=50,
        strengths=["Answer was submitted and recorded."],
        weaknesses=["Automated evaluation was temporarily unavailable for this answer."],
        suggestions=["Please retry evaluation, or review this answer manually."],
        sample_answer="",
    )


def evaluate_answer(db: Session, interview: Interview, question: Question, answer: Answer) -> Feedback:
    grounding_chunks = []
    if question.grounding_chunk_ids:
        grounding_chunks = (
            db.query(DocumentChunk).filter(DocumentChunk.id.in_(question.grounding_chunk_ids)).all()
        )
    context = "\n---\n".join(c.content for c in grounding_chunks) if grounding_chunks else "(no grounding context)"

    system_prompt = EVALUATOR_SYSTEM.format(
        interview_type=interview.type,
        target_role=interview.target_role,
        experience_level=interview.experience_level,
    )
    user_prompt = (
        f"Question category: {question.category}\n"
        f"Question: {question.text}\n\n"
        f"Candidate's answer:\n{answer.text}\n\n"
        f"Grounding context used for the question:\n{context}\n\n"
        "Return the evaluation JSON."
    )

    llm = get_llm_provider()
    try:
        result = call_llm_for_json(llm, EvaluationResult, system_prompt, user_prompt, max_tokens=1200)
    except (ValueError, RuntimeError):
        result = _fallback_evaluation()

    score = question_score(
        question.category,
        {
            "correctness": result.correctness,
            "relevance": result.relevance,
            "technical_accuracy": result.technical_accuracy,
            "completeness": result.completeness,
            "communication": result.communication,
        },
    )

    feedback = Feedback(
        answer_id=answer.id,
        score=score,
        correctness=result.correctness,
        relevance=result.relevance,
        technical_accuracy=result.technical_accuracy,
        completeness=result.completeness,
        communication=result.communication,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        suggestions=result.suggestions,
        sample_answer=result.sample_answer or None,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
