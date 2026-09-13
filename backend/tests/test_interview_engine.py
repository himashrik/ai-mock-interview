import uuid

from app.models.interview import Answer, Feedback, Interview, Question
from app.services.interview_engine import (
    FALLBACK_QUESTIONS,
    MIXED_ROTATION,
    _adaptive_difficulty,
    _category_for_index,
    _decide_category_and_followup,
    generate_next_question,
)


def _make_general_interview(db_session, interview_type="technical", num_questions=6):
    interview = Interview(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        type=interview_type, target_role="Backend Engineer", experience_level="junior",
        difficulty="medium", mode="general", num_questions=num_questions,
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)
    return interview


def test_category_for_index_non_mixed_is_constant():
    assert _category_for_index("technical", 0) == "technical"
    assert _category_for_index("technical", 5) == "technical"


def test_category_for_index_mixed_rotates_through_all_categories():
    seen = {_category_for_index("mixed", i) for i in range(len(MIXED_ROTATION) * 2)}
    assert seen == set(MIXED_ROTATION)


def test_generate_next_question_uses_llm_output(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.interview_engine")
    fake.json_responses = [
        '{"question": "Explain how a hash map works.", "category": "technical", '
        '"difficulty": "medium", "source": "general", "grounded_on": "none"}'
    ]

    interview = _make_general_interview(db_session)
    question = generate_next_question(db_session, interview, question_index=0)

    assert question.text == "Explain how a hash map works."
    assert question.interview_id == interview.id
    assert question.index == 0
    # persisted, not just returned in memory
    stored = db_session.get(Question, question.id)
    assert stored is not None


def test_generate_next_question_falls_back_on_llm_failure(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.interview_engine")
    fake.json_responses = ["not valid json", "still not valid json"]  # exhausts retries -> ValueError path

    interview = _make_general_interview(db_session, interview_type="hr")
    question = generate_next_question(db_session, interview, question_index=0)

    assert question.text == FALLBACK_QUESTIONS["hr"]
    assert question.source == "general"


def test_generate_next_question_never_repeats_previous_questions_in_prompt(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.interview_engine")
    fake.json_responses = [
        '{"question": "First technical question here", "category": "technical", "difficulty": "medium", "source": "general", "grounded_on": "none"}',
        '{"question": "Second technical question here", "category": "technical", "difficulty": "medium", "source": "general", "grounded_on": "none"}',
    ]
    interview = _make_general_interview(db_session)

    q1 = generate_next_question(db_session, interview, question_index=0)
    q2 = generate_next_question(db_session, interview, question_index=1)

    assert q1.text == "First technical question here" and q2.text == "Second technical question here"
    # the second call's prompt must have included the first question's text as "previously asked"
    _, _, second_user_prompt = fake.calls[1]
    assert "First technical question here" in second_user_prompt


def _add_answered_question(db_session, interview, index, category, score, weaknesses, source="general"):
    question = Question(
        interview_id=interview.id, index=index, category=category, text=f"Question {index}",
        difficulty="medium", source=source,
    )
    db_session.add(question); db_session.commit(); db_session.refresh(question)

    answer = Answer(question_id=question.id, interview_id=interview.id, user_id=interview.user_id, text="An answer")
    db_session.add(answer); db_session.commit(); db_session.refresh(answer)

    feedback = Feedback(
        answer_id=answer.id, score=score, correctness=score, relevance=score, technical_accuracy=score,
        completeness=score, communication=score, weaknesses=weaknesses, strengths=[], suggestions=[],
    )
    db_session.add(feedback); db_session.commit()
    return question, answer, feedback


def test_weak_answer_in_eligible_category_triggers_followup(db_session):
    interview = _make_general_interview(db_session, interview_type="technical")
    _add_answered_question(
        db_session, interview, index=0, category="technical", score=30,
        weaknesses=["Did not explain collision handling"],
    )
    category, is_followup, weakness_context = _decide_category_and_followup(db_session, interview, question_index=1)
    assert is_followup is True
    assert category == "technical"
    assert "collision handling" in weakness_context


def test_strong_answer_does_not_trigger_followup(db_session):
    interview = _make_general_interview(db_session, interview_type="technical")
    _add_answered_question(
        db_session, interview, index=0, category="technical", score=90, weaknesses=["Minor nitpick"],
    )
    _, is_followup, _ = _decide_category_and_followup(db_session, interview, question_index=1)
    assert is_followup is False


def test_followup_never_chains_twice_in_a_row(db_session):
    interview = _make_general_interview(db_session, interview_type="technical")
    # A weak followup question that was itself answered weakly should NOT trigger yet another followup.
    _add_answered_question(
        db_session, interview, index=0, category="technical", score=20,
        weaknesses=["Still vague"], source="followup",
    )
    _, is_followup, _ = _decide_category_and_followup(db_session, interview, question_index=1)
    assert is_followup is False


def test_aptitude_category_never_triggers_followup(db_session):
    interview = _make_general_interview(db_session, interview_type="aptitude")
    _add_answered_question(
        db_session, interview, index=0, category="aptitude", score=10, weaknesses=["Wrong calculation"],
    )
    _, is_followup, _ = _decide_category_and_followup(db_session, interview, question_index=1)
    assert is_followup is False


def test_generate_next_question_marks_followup_source_even_if_llm_forgets(db_session, patch_llm_provider):
    fake = patch_llm_provider("app.services.interview_engine")
    interview = _make_general_interview(db_session, interview_type="technical")
    _add_answered_question(
        db_session, interview, index=0, category="technical", score=25,
        weaknesses=["Missed the concurrency angle entirely"],
    )
    # LLM response omits "source": "followup" (defaults to "general") -- our own routing decision
    # must win regardless, since the guarantee against chained followups depends on it.
    fake.json_responses = [
        '{"question": "Can you say more about the concurrency handling?", "category": "technical", '
        '"difficulty": "medium", "grounded_on": "none"}'
    ]
    question = generate_next_question(db_session, interview, question_index=1)
    assert question.source == "followup"

    _, system_prompt, user_prompt = fake.calls[0]
    assert "FOLLOW-UP" in user_prompt
    assert "concurrency" in user_prompt.lower() or "Missed the concurrency angle entirely" in user_prompt


def test_adaptive_difficulty_holds_steady_with_no_answers_yet(db_session):
    interview = _make_general_interview(db_session, interview_type="technical")
    interview.difficulty = "medium"
    assert _adaptive_difficulty(db_session, interview) == "medium"


def test_adaptive_difficulty_escalates_after_strong_run(db_session):
    interview = _make_general_interview(db_session, interview_type="technical")
    interview.difficulty = "medium"
    for i in range(3):
        _add_answered_question(db_session, interview, index=i, category="technical", score=90, weaknesses=[])
    assert _adaptive_difficulty(db_session, interview) == "hard"


def test_adaptive_difficulty_de_escalates_after_weak_run(db_session):
    interview = _make_general_interview(db_session, interview_type="technical")
    interview.difficulty = "medium"
    for i in range(3):
        _add_answered_question(db_session, interview, index=i, category="technical", score=25, weaknesses=["Gap"])
    assert _adaptive_difficulty(db_session, interview) == "easy"
