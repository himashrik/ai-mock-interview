import pytest
from pydantic import BaseModel

from app.services.llm_json import call_llm_for_json
from tests.conftest import FakeLLMProvider


class Sample(BaseModel):
    question: str
    score: int


def test_call_llm_for_json_parses_clean_json():
    llm = FakeLLMProvider(json_responses=['{"question": "Tell me about yourself", "score": 80}'])
    result = call_llm_for_json(llm, Sample, "system", "user")
    assert result.question == "Tell me about yourself"
    assert result.score == 80


def test_call_llm_for_json_strips_markdown_fences():
    llm = FakeLLMProvider(json_responses=['```json\n{"question": "Q1", "score": 50}\n```'])
    result = call_llm_for_json(llm, Sample, "system", "user")
    assert result.question == "Q1"


def test_call_llm_for_json_retries_once_on_malformed_json():
    llm = FakeLLMProvider(json_responses=[
        "not json at all",
        '{"question": "Recovered", "score": 90}',
    ])
    result = call_llm_for_json(llm, Sample, "system", "user", max_retries=1)
    assert result.question == "Recovered"
    assert len(llm.calls) == 2  # confirms a retry actually happened


def test_call_llm_for_json_retries_once_on_schema_validation_failure():
    llm = FakeLLMProvider(json_responses=[
        '{"question": "Missing score field"}',
        '{"question": "Fixed", "score": 70}',
    ])
    result = call_llm_for_json(llm, Sample, "system", "user", max_retries=1)
    assert result.score == 70


def test_call_llm_for_json_raises_after_exhausting_retries():
    llm = FakeLLMProvider(json_responses=["garbage", "still garbage"])
    with pytest.raises(ValueError):
        call_llm_for_json(llm, Sample, "system", "user", max_retries=1)


def test_call_llm_for_json_never_trusts_unvalidated_data():
    # Extra/wrong-typed fields should not silently pass through as valid.
    llm = FakeLLMProvider(json_responses=['{"question": "Q", "score": "not-a-number"}', '{"question": "Q", "score": 1}'])
    result = call_llm_for_json(llm, Sample, "system", "user", max_retries=1)
    assert isinstance(result.score, int)
