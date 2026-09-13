import uuid

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.prompts import INTERVIEWER_SYSTEM, CATEGORY_GUIDANCE
from app.llm.factory import get_llm_provider
from app.models.interview import Interview, Question, Answer
from app.models.interview import Feedback
from app.services.llm_json import call_llm_for_json
from app.services.scoring import suggest_next_difficulty
from app.services.vector_store import retrieve_relevant_chunks

MIXED_ROTATION = ["hr", "technical", "behavioral", "aptitude"]

# Categories where "ask a deeper follow-up on the same topic" is a natural interviewer move.
# Aptitude and GD questions are typically self-contained, so we don't chain follow-ups there.
FOLLOWUP_ELIGIBLE_CATEGORIES = {"hr", "technical", "behavioral"}
FOLLOWUP_SCORE_THRESHOLD = 55  # below this, the previous answer likely had a real gap worth probing

FALLBACK_QUESTIONS = {
    "hr": "Tell me about yourself and why you're interested in this role.",
    "technical": "Walk me through the architecture of a project you're proud of and the trade-offs you made.",
    "aptitude": "A train travels 60 km in 45 minutes. At the same speed, how long will it take to travel 100 km?",
    "behavioral": "Describe a time you disagreed with a teammate's approach. What did you do?",
    "gd": "Should companies allow fully remote work for all engineering roles? State and defend a position.",
    "mixed": "Tell me about yourself and one technical project you'd like to highlight.",
}

FALLBACK_FOLLOWUPS = {
    "hr": "Can you go a bit deeper on that? What specifically was your role, and what was the outcome?",
    "technical": "Can you go into more detail on that? Walk me through the specific implementation and why you chose it.",
    "behavioral": "Can you say more about that? Specifically, what was the measurable result of your action?",
}


class GeneratedQuestion(BaseModel):
    question: str = Field(min_length=5)
    category: str
    difficulty: str = "medium"
    source: str = "general"
    grounded_on: str = "none"


def _category_for_index(interview_type: str, index: int) -> str:
    if interview_type != "mixed":
        return interview_type
    return MIXED_ROTATION[index % len(MIXED_ROTATION)]


def _last_answered_turn(db: Session, interview_id: uuid.UUID):
    """Returns (question, answer, feedback) for the most recently answered question, or None."""
    row = (
        db.execute(
            select(Question, Answer, Feedback)
            .join(Answer, Answer.question_id == Question.id)
            .join(Feedback, Feedback.answer_id == Answer.id)
            .where(Question.interview_id == interview_id)
            .order_by(Question.index.desc())
            .limit(1)
        )
        .first()
    )
    return row


def _decide_category_and_followup(
    db: Session, interview: Interview, question_index: int
) -> tuple[str, bool, str | None]:
    """Decides the next question's category, whether it should be an adaptive follow-up on the
    candidate's previous (weak) answer, and — if so — a short note describing the specific gap
    to probe. This is what makes the interview "adaptive" rather than a fixed script:
    a weak answer in a follow-up-eligible category gets one probing follow-up before the
    interview moves on; a strong answer just proceeds to the next topic as normal."""
    base_category = _category_for_index(interview.type, question_index)

    if question_index == 0:
        return base_category, False, None

    last_turn = _last_answered_turn(db, interview.id)
    if last_turn is None:
        return base_category, False, None

    last_question, last_answer, last_feedback = last_turn

    # Never chain two follow-ups back to back -- one probe is enough before moving on.
    if last_question.source == "followup":
        return base_category, False, None
    if last_question.category not in FOLLOWUP_ELIGIBLE_CATEGORIES:
        return base_category, False, None
    if last_feedback.score >= FOLLOWUP_SCORE_THRESHOLD:
        return base_category, False, None
    if not last_feedback.weaknesses:
        return base_category, False, None

    weakness_context = (
        f'Their previous answer to "{last_question.text[:150]}" scored {last_feedback.score}/100. '
        f"The specific gap identified was: {last_feedback.weaknesses[0]}"
    )
    return last_question.category, True, weakness_context


def _adaptive_difficulty(db: Session, interview: Interview) -> str:
    """Walks the interview's configured starting difficulty toward wherever the candidate's
    running performance suggests, so a strong start ramps up and a shaky start eases off --
    rather than asking every question at a single fixed difficulty regardless of how it's going."""
    scores = [
        f.score
        for f in db.execute(
            select(Feedback).join(Answer, Feedback.answer_id == Answer.id).where(Answer.interview_id == interview.id)
        ).scalars().all()
    ]
    if not scores:
        return interview.difficulty
    running_average = sum(scores) / len(scores)
    return suggest_next_difficulty(interview.difficulty, running_average)


def _conversation_summary(db: Session, interview_id: uuid.UUID) -> str:
    rows = (
        db.execute(
            select(Question, Answer, Feedback)
            .join(Answer, Answer.question_id == Question.id, isouter=True)
            .join(Feedback, Feedback.answer_id == Answer.id, isouter=True)
            .where(Question.interview_id == interview_id)
            .order_by(Question.index)
        )
        .all()
    )
    if not rows:
        return "No questions answered yet."

    lines = []
    for q, a, f in rows:
        if a is None:
            continue
        score_note = f", score={f.score}" if f else ""
        lines.append(f"[{q.category}{score_note}] Q: {q.text[:150]} | A(excerpt): {a.text[:150]}")
    return "\n".join(lines) if lines else "No questions answered yet."


def generate_next_question(db: Session, interview: Interview, question_index: int) -> Question:
    category, is_followup, weakness_context = _decide_category_and_followup(db, interview, question_index)
    difficulty = _adaptive_difficulty(db, interview)

    query = f"{interview.target_role} {category} relevant background skills projects experience"
    doc_types = []
    if interview.mode == "resume":
        if interview.resume_document_id:
            doc_types.append("resume")
        if interview.jd_document_id:
            doc_types.append("jd")

    chunks = []
    if doc_types:
        chunks = retrieve_relevant_chunks(
            db, user_id=interview.user_id, query=query, document_types=doc_types, top_k=4
        )
    context = "\n---\n".join(c.content for c in chunks) if chunks else "(no resume/JD context — general mode)"

    previously_asked = [
        q.text for q in db.execute(
            select(Question).where(Question.interview_id == interview.id)
        ).scalars().all()
    ]
    summary = _conversation_summary(db, interview.id)

    system_prompt = INTERVIEWER_SYSTEM.format(
        interview_type=interview.type,
        target_role=interview.target_role,
        experience_level=interview.experience_level,
        difficulty=difficulty,
        category_guidance=CATEGORY_GUIDANCE.get(category, CATEGORY_GUIDANCE["mixed"]),
    )

    followup_instruction = ""
    if is_followup:
        followup_instruction = (
            f"\n\nIMPORTANT: This turn should be a FOLLOW-UP question, not a new topic. "
            f"{weakness_context}\n"
            f'Ask a single, specific follow-up question that gives the candidate a chance to address '
            f"that exact gap -- don't just repeat the original question, and don't change topics. "
            f'Set "source" to "followup" in your response.'
        )

    user_prompt = (
        f"Context chunks:\n{context}\n\n"
        f"Previously asked questions: {previously_asked}\n\n"
        f"Conversation summary so far:\n{summary}\n\n"
        f"This is question #{question_index + 1} of {interview.num_questions}. "
        f"Current adaptive difficulty based on performance so far: {difficulty}.{followup_instruction}\n\n"
        f"Generate the next question now."
    )

    llm = get_llm_provider()
    try:
        result = call_llm_for_json(llm, GeneratedQuestion, system_prompt, user_prompt, max_tokens=600)
    except (ValueError, RuntimeError):
        fallback_text = (
            FALLBACK_FOLLOWUPS.get(category, FALLBACK_QUESTIONS.get(category, FALLBACK_QUESTIONS["mixed"]))
            if is_followup
            else FALLBACK_QUESTIONS.get(category, FALLBACK_QUESTIONS["mixed"])
        )
        result = GeneratedQuestion(
            question=fallback_text,
            category=category,
            difficulty=difficulty,
            source="followup" if is_followup else "general",
            grounded_on="fallback template (LLM unavailable)",
        )

    # Trust our own follow-up decision over whatever the model echoed back in "source" -- the
    # model is asked to set it, but the actual routing decision (and thus the guarantee that we
    # never chain two follow-ups in a row) lives in _decide_category_and_followup, not the LLM.
    final_source = "followup" if is_followup else result.source

    question = Question(
        interview_id=interview.id,
        index=question_index,
        category=category,
        text=result.question,
        difficulty=result.difficulty or difficulty,
        source=final_source,
        grounding_chunk_ids=[str(c.id) for c in chunks],
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question
