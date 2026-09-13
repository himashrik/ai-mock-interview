from openai import OpenAI

from app.core.config import settings
from app.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def _call(self, system_prompt: str, user_prompt: str, max_tokens: int, force_json: bool) -> str:
        kwargs = {}
        if force_json:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            **kwargs,
        )
        return (response.choices[0].message.content or "").strip()

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
        return self._call(system_prompt, user_prompt, max_tokens, force_json=True)

    def complete_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
        return self._call(system_prompt, user_prompt, max_tokens, force_json=False)
