import uuid

from app.models.interview import Answer, Feedback, Interview, Question, Report
from app.services.report_generator import generate_report


def _build_completed_interview(db_session):
    interview = Interview(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        type="mixed", target_role="Backend Engineer", experience_level="mid",
        difficulty="medium", mode="general", num_questions=2,
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)

    # Question 1: technical, scored high
    q1 = Question(interview_id=interview.id, index=0, category="technical", text="Q1", difficulty="medium", source="general")
    db_session.add(q1); db_session.commit(); db_session.refresh(q1)
    a1 = Answer(question_id=q1.id, interview_id=interview.id, user_id=interview.user_id, text="Answer 1")
    db_session.add(a1); db_session.commit(); db_session.refresh(a1)
    f1 = Feedback(
        answer_id=a1.id, score=90, correctness=90, relevance=90, technical_accuracy=90,
        completeness=90, communication=90, strengths=["Strong"], weaknesses=[], suggestions=[],
    )
    db_session.add(f1)

    # Question 2: hr, scored low
    q2 = Question(interview_id=interview.id, index=1, category="hr", text="Q2", difficulty="medium", source="general")
    db_session.add(q2); db_session.commit(); db_session.refresh(q2)
    a2 = Answer(question_id=q2.id, interview_id=interview.id, user_id=interview.user_id, text="Answer 2")
    db_session.add(a2); db_session.commit(); db_session.refresh(a2)
    f2 = Feedback(
        answer_id=a2.id, score=40, correctness=40, relevance=40, technical_accuracy=0,
        completeness=40, communication=40, strengths=[], weaknesses=["Too vague"], suggestions=[],
    )
    db_session.add(f2)
    db_session.commit()

    return interview


def test_generate_report_computes_correct_overall_and_category_scores(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.report_generator")
    fake.json_responses = [
        '{"strongest_areas": ["Technical"], "weakest_areas": ["HR"], "common_mistakes": ["Vague HR answers"], '
        '"study_plan": ["Practice STAR method"], "tips": ["Be concise"], "resume_alignment_notes": ""}'
    ]

    interview = _build_completed_interview(db_session)
    report = generate_report(db_session, interview)

    assert report.overall_score == 65.0  # mean of 90 and 40
    assert report.category_scores == {"technical": 90.0, "hr": 40.0}
    assert report.next_difficulty in ("easy", "medium", "hard")

    # side effects: interview flipped to completed with a timestamp and overall_score set
    db_session.refresh(interview)
    assert interview.status == "completed"
    assert interview.overall_score == 65.0
    assert interview.completed_at is not None


def test_generate_report_persists_a_single_report_row(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.report_generator")
    fake.json_responses = [
        '{"strongest_areas": [], "weakest_areas": [], "common_mistakes": [], "study_plan": [], "tips": [], "resume_alignment_notes": ""}'
    ]
    interview = _build_completed_interview(db_session)
    generate_report(db_session, interview)

    reports = db_session.query(Report).filter(Report.interview_id == interview.id).all()
    assert len(reports) == 1


def test_generate_report_falls_back_to_computed_narrative_on_llm_failure(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.report_generator")
    fake.json_responses = ["garbage", "still garbage"]

    interview = _build_completed_interview(db_session)
    report = generate_report(db_session, interview)

    # Scores are always computed in Python regardless of LLM success, so this must hold even in fallback.
    assert report.overall_score == 65.0
    assert len(report.weakest_areas) > 0  # fallback narrative still identifies the weak category
