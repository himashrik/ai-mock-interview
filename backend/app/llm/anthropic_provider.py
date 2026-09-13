import anthropic

from app.core.config import settings
from app.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL

    def _call(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        return "".join(parts).strip()

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
        strict_system = (
            system_prompt
            + "\n\nRespond with ONLY a single valid JSON object. No markdown code fences, "
            "no preamble, no explanation before or after the JSON."
        )
        return self._call(strict_system, user_prompt, max_tokens)

    def complete_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
        return self._call(system_prompt, user_prompt, max_tokens)
