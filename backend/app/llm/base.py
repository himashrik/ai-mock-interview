from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Common interface so the rest of the app never depends on a specific vendor SDK."""

    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
        """Send a prompt and return the raw text response (expected to be JSON).

        Implementations should instruct the underlying model to return ONLY JSON,
        with no markdown fences or preamble. Callers are responsible for parsing
        and validating the result (see app/services/llm_json.py).
        """
        raise NotImplementedError

    @abstractmethod
    def complete_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
        """Send a prompt and return free-form text (used for narrative report sections)."""
        raise NotImplementedError
