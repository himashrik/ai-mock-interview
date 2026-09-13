import uuid

from app.models.interview import Answer, Interview, Question
from app.services.evaluator import evaluate_answer
from app.services.scoring import question_score


def _setup_interview_question_answer(db_session, category="technical"):
    interview = Interview(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        type=category, target_role="Backend Engineer", experience_level="mid",
        difficulty="medium", mode="general", num_questions=3,
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)

    question = Question(
        interview_id=interview.id, index=0, category=category, text="Explain a hash map.",
        difficulty="medium", source="general", grounding_chunk_ids=[],
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)

    answer = Answer(
        question_id=question.id, interview_id=interview.id, user_id=interview.user_id,
        text="A hash map uses a hash function to map keys to array indices for O(1) average lookup.",
    )
    db_session.add(answer)
    db_session.commit()
    db_session.refresh(answer)

    return interview, question, answer


def test_evaluate_answer_computes_score_via_scoring_formula(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.evaluator")
    fake.json_responses = [
        '{"correctness": 90, "relevance": 85, "technical_accuracy": 95, "completeness": 80, '
        '"communication": 88, "strengths": ["Explained O(1) lookup clearly"], '
        '"weaknesses": ["Did not mention collision handling"], '
        '"suggestions": ["Mention how collisions are resolved"], "sample_answer": "..."}'
    ]

    interview, question, answer = _setup_interview_question_answer(db_session)
    feedback = evaluate_answer(db_session, interview, question, answer)

    expected = question_score("technical", {
        "correctness": 90, "relevance": 85, "technical_accuracy": 95,
        "completeness": 80, "communication": 88,
    })
    assert feedback.score == expected
    assert "collision handling" in feedback.weaknesses[0]


def test_evaluate_answer_references_actual_answer_content_in_prompt(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.evaluator")
    fake.json_responses = [
        '{"correctness": 70, "relevance": 70, "technical_accuracy": 70, "completeness": 70, '
        '"communication": 70, "strengths": [], "weaknesses": [], "suggestions": [], "sample_answer": ""}'
    ]
    interview, question, answer = _setup_interview_question_answer(db_session)
    evaluate_answer(db_session, interview, question, answer)

    _, _, user_prompt = fake.calls[0]
    assert answer.text in user_prompt
    assert question.text in user_prompt


def test_evaluate_answer_falls_back_gracefully_on_llm_failure(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.evaluator")
    fake.json_responses = ["garbage", "still garbage"]

    interview, question, answer = _setup_interview_question_answer(db_session, category="hr")
    feedback = evaluate_answer(db_session, interview, question, answer)

    # Fallback evaluation should still produce a persisted, plausible feedback row -- never crash the request.
    assert feedback.score > 0
    assert feedback.id is not None


def test_evaluate_answer_zeroes_technical_accuracy_weight_for_hr(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.evaluator")
    fake.json_responses = [
        '{"correctness": 80, "relevance": 80, "technical_accuracy": 0, "completeness": 80, '
        '"communication": 80, "strengths": [], "weaknesses": [], "suggestions": [], "sample_answer": ""}'
    ]
    interview, question, answer = _setup_interview_question_answer(db_session, category="hr")
    feedback = evaluate_answer(db_session, interview, question, answer)
    assert feedback.score == 80.0  # all non-zero-weighted dims are 80, technical_accuracy weight is 0
