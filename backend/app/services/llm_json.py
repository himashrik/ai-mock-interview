import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.base import LLMProvider

T = TypeVar("T", bound=BaseModel)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_str(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[-1] if "\n" in raw else raw
    match = _JSON_BLOCK_RE.search(raw)
    return match.group(0) if match else raw


def call_llm_for_json(
    llm: LLMProvider,
    schema: type[T],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1500,
    max_retries: int = 1,
) -> T:
    """Call the LLM, parse+validate the JSON response against `schema`.

    On failure, retries once with the validation error fed back to the model so it
    can self-correct. Raises ValueError if it still fails after retries — callers
    should catch this and fall back to a safe default rather than trusting bad data.
    """
    last_error: Exception | None = None
    prompt = user_prompt

    for attempt in range(max_retries + 1):
        raw = llm.complete_json(system_prompt, prompt, max_tokens=max_tokens)
        json_str = _extract_json_str(raw)
        try:
            data = json.loads(json_str)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            prompt = (
                f"{user_prompt}\n\n"
                f"Your previous response could not be parsed/validated: {e}\n"
                f"Previous response was: {raw}\n"
                f"Return ONLY a corrected, valid JSON object matching the required schema."
            )

    raise ValueError(f"LLM did not return valid JSON matching {schema.__name__} after retries: {last_error}")
