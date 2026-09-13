from collections import defaultdict

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.prompts import REPORT_NARRATIVE_SYSTEM
from app.llm.factory import get_llm_provider
from app.models.interview import Answer, Feedback, Interview, Question, Report
from app.services.scoring import aggregate_category_scores, overall_score, suggest_next_difficulty


class NarrativeSections(BaseModel):
    strongest_areas: list[str] = []
    weakest_areas: list[str] = []
    common_mistakes: list[str] = []
    study_plan: list[str] = []
    tips: list[str] = []
    resume_alignment_notes: str = ""


def _fallback_narrative(category_scores: dict[str, float]) -> NarrativeSections:
    if not category_scores:
        return NarrativeSections(
            weakest_areas=["Not enough answered questions to determine weak areas."],
            tips=["Complete a full interview to receive a detailed narrative report."],
        )
    ranked = sorted(category_scores.items(), key=lambda kv: kv[1], reverse=True)
    strong = [c for c, s in ranked if s >= 70][:2] or [ranked[0][0]]
    weak = [c for c, s in ranked if s < 70][:2] or [ranked[-1][0]]
    return NarrativeSections(
        strongest_areas=[f"{c.title()} (avg {category_scores[c]})" for c in strong],
        weakest_areas=[f"{c.title()} (avg {category_scores[c]})" for c in weak],
        common_mistakes=["Automated narrative generation was unavailable; review per-question feedback below."],
        study_plan=[f"Review fundamentals and practice more {c} questions." for c in weak],
        tips=["Practice structuring answers before speaking.", "Quantify impact wherever possible."],
        resume_alignment_notes="",
    )


def generate_report(db: Session, interview: Interview) -> Report:
    rows = (
        db.execute(
            select(Question, Answer, Feedback)
            .join(Answer, Answer.question_id == Question.id, isouter=True)
            .join(Feedback, Feedback.answer_id == Answer.id, isouter=True)
            .where(Question.interview_id == interview.id)
            .order_by(Question.index)
        )
        .all()
    )

    scores_by_category: dict[str, list[float]] = defaultdict(list)
    all_scores: list[float] = []
    qa_summary_lines = []

    for q, a, f in rows:
        if f is None:
            continue
        scores_by_category[q.category].append(f.score)
        all_scores.append(f.score)
        qa_summary_lines.append(
            f"Q{q.index + 1} [{q.category}] score={f.score}: {q.text[:120]} -- "
            f"weaknesses={f.weaknesses[:2]}"
        )

    category_scores = aggregate_category_scores(scores_by_category)
    final_overall = overall_score(all_scores)
    next_difficulty = suggest_next_difficulty(interview.difficulty, final_overall)

    llm = get_llm_provider()
    narrative = None
    try:
        from app.services.llm_json import call_llm_for_json

        narrative = call_llm_for_json(
            llm,
            NarrativeSections,
            REPORT_NARRATIVE_SYSTEM,
            f"Interview type: {interview.type}, role: {interview.target_role}\n"
            f"Overall score: {final_overall}\nCategory scores: {category_scores}\n"
            f"Per-question summary:\n" + "\n".join(qa_summary_lines) + "\n\n"
            "Write the narrative report sections JSON.",
            max_tokens=1500,
        )
    except (ValueError, RuntimeError):
        narrative = _fallback_narrative(category_scores)

    report = Report(
        interview_id=interview.id,
        overall_score=final_overall,
        category_scores=category_scores,
        strongest_areas=narrative.strongest_areas,
        weakest_areas=narrative.weakest_areas,
        common_mistakes=narrative.common_mistakes,
        study_plan=narrative.study_plan,
        tips=narrative.tips,
        next_difficulty=next_difficulty,
        resume_alignment_notes=narrative.resume_alignment_notes or None,
    )
    db.add(report)
    interview.overall_score = final_overall
    interview.status = "completed"
    from datetime import datetime, timezone
    interview.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report
