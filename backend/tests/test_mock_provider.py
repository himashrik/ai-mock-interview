from app.core.prompts import (
    ASSISTANT_SYSTEM,
    ATS_ANALYSIS_SYSTEM,
    EVALUATOR_SYSTEM,
    INTERVIEWER_SYSTEM,
    JD_ANALYSIS_SYSTEM,
    REPORT_NARRATIVE_SYSTEM,
    RESUME_ANALYSIS_SYSTEM,
    CATEGORY_GUIDANCE,
)
from app.llm.mock_provider import DEMO_NOTICE, MockLLMProvider
from app.services.ats_analyzer import AtsAnalysisResult
from app.services.evaluator import EvaluationResult
from app.services.interview_engine import GeneratedQuestion
from app.services.llm_json import call_llm_for_json
from app.services.report_generator import NarrativeSections
from app.schemas.document import JDAnalysis, ResumeAnalysis


def test_mock_provider_produces_valid_question_json():
    llm = MockLLMProvider()
    system_prompt = INTERVIEWER_SYSTEM.format(
        interview_type="technical", target_role="Backend Engineer", experience_level="mid",
        difficulty="medium", category_guidance=CATEGORY_GUIDANCE["technical"],
    )
    result = call_llm_for_json(llm, GeneratedQuestion, system_prompt, "Generate the next question now.")
    assert len(result.question) >= 5
    assert result.category == "technical"


def test_mock_provider_produces_valid_evaluation_json():
    llm = MockLLMProvider()
    system_prompt = EVALUATOR_SYSTEM.format(interview_type="hr", target_role="PM", experience_level="junior")
    user_prompt = "Question: Tell me about yourself\n\nCandidate's answer:\nI'm a product manager.\n\nGrounding context used: none"
    result = call_llm_for_json(llm, EvaluationResult, system_prompt, user_prompt)
    assert 0 <= result.correctness <= 100
    assert DEMO_NOTICE in result.weaknesses


def test_mock_provider_produces_valid_resume_analysis_json():
    llm = MockLLMProvider()
    result = call_llm_for_json(llm, ResumeAnalysis, RESUME_ANALYSIS_SYSTEM, "Resume content chunks:\n...")
    assert DEMO_NOTICE in result.missing_information


def test_mock_provider_produces_valid_jd_analysis_json():
    llm = MockLLMProvider()
    result = call_llm_for_json(llm, JDAnalysis, JD_ANALYSIS_SYSTEM, "JD content chunks:\n...")
    assert result.target_role == DEMO_NOTICE


def test_mock_provider_produces_valid_ats_analysis_json():
    llm = MockLLMProvider()
    result = call_llm_for_json(llm, AtsAnalysisResult, ATS_ANALYSIS_SYSTEM, "RESUME:\n...\n\nJD:\n...")
    assert 0 <= result.score <= 100


def test_mock_provider_produces_valid_narrative_json():
    llm = MockLLMProvider()
    result = call_llm_for_json(llm, NarrativeSections, REPORT_NARRATIVE_SYSTEM, "Overall score: 70")
    assert DEMO_NOTICE in result.study_plan


def test_mock_provider_chat_reply_is_labeled_as_demo_content():
    llm = MockLLMProvider()
    reply = llm.complete_text(ASSISTANT_SYSTEM, "User's new message: How do I use the STAR method?\n\nRespond as the assistant.")
    assert "Demo mode" in reply
    assert "STAR" in reply or "Situation" in reply


def test_mock_provider_question_bank_respects_category():
    llm = MockLLMProvider()
    for category in ["hr", "technical", "aptitude", "behavioral"]:
        system_prompt = INTERVIEWER_SYSTEM.format(
            interview_type=category, target_role="X", experience_level="junior",
            difficulty="medium", category_guidance=CATEGORY_GUIDANCE[category],
        )
        result = call_llm_for_json(llm, GeneratedQuestion, system_prompt, "go")
        assert result.category == category


def test_mock_provider_evaluation_score_varies_with_answer_content():
    llm = MockLLMProvider()
    system_prompt = EVALUATOR_SYSTEM.format(interview_type="technical", target_role="X", experience_level="mid")

    prompt_a = "Candidate's answer:\nShort answer.\n\nGrounding context used: none"
    prompt_b = "Candidate's answer:\nA completely different and much longer answer about distributed systems.\n\nGrounding context used: none"

    result_a = call_llm_for_json(llm, EvaluationResult, system_prompt, prompt_a)
    result_b = call_llm_for_json(llm, EvaluationResult, system_prompt, prompt_b)
    # Not asserting a specific relationship (it's a hash, not real understanding) -- just that
    # different answers produce different scores, so a demo doesn't look suspiciously static.
    assert result_a.correctness != result_b.correctness
