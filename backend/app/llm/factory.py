import logging
from functools import lru_cache

from app.core.config import settings
from app.llm.base import LLMProvider

logger = logging.getLogger("ai_interview_platform")

# Set by get_llm_provider() the first time it runs, so other parts of the app (e.g. the
# /system/status endpoint) can report which provider is actually active -- this can differ from
# settings.LLM_PROVIDER if we fell back to the mock provider due to a missing API key.
active_provider_name: str = "unresolved"


@lru_cache
def get_llm_provider() -> LLMProvider:
    global active_provider_name

    if settings.LLM_PROVIDER == "mock":
        active_provider_name = "mock"
        return _mock()

    try:
        if settings.LLM_PROVIDER == "openai":
            from app.llm.openai_provider import OpenAIProvider
            provider = OpenAIProvider()
            active_provider_name = "openai"
        else:
            from app.llm.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider()
            active_provider_name = "anthropic"
        return provider
    except RuntimeError as e:
        # Missing API key: fall back to the mock provider rather than making every AI-dependent
        # request in the app fail outright. This is what makes `docker compose up` with an empty
        # .env produce a fully working (if template-content) demo instead of a broken one.
        logger.warning(
            "LLM_PROVIDER=%s but no API key is configured (%s) -- falling back to the mock LLM "
            "provider. Set the relevant API key in .env for real AI-generated content.",
            settings.LLM_PROVIDER, e,
        )
        active_provider_name = "mock"
        return _mock()


def _mock() -> LLMProvider:
    from app.llm.mock_provider import MockLLMProvider
    return MockLLMProvider()
