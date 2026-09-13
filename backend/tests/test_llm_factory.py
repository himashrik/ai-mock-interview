from app.llm import factory
from app.llm.mock_provider import MockLLMProvider


def _reset_factory_cache():
    factory.get_llm_provider.cache_clear()
    factory.active_provider_name = "unresolved"


def test_factory_falls_back_to_mock_when_anthropic_key_missing(monkeypatch):
    _reset_factory_cache()
    monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "anthropic")
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "")

    provider = factory.get_llm_provider()

    assert isinstance(provider, MockLLMProvider)
    assert factory.active_provider_name == "mock"
    _reset_factory_cache()


def test_factory_falls_back_to_mock_when_openai_key_missing(monkeypatch):
    _reset_factory_cache()
    monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "openai")
    monkeypatch.setattr("app.core.config.settings.OPENAI_API_KEY", "")

    provider = factory.get_llm_provider()

    assert isinstance(provider, MockLLMProvider)
    assert factory.active_provider_name == "mock"
    _reset_factory_cache()


def test_factory_explicit_mock_provider(monkeypatch):
    _reset_factory_cache()
    monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "mock")

    provider = factory.get_llm_provider()

    assert isinstance(provider, MockLLMProvider)
    assert factory.active_provider_name == "mock"
    _reset_factory_cache()


def test_system_status_endpoint_reports_demo_mode(client, monkeypatch):
    _reset_factory_cache()
    monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "mock")

    resp = client.get("/system/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_provider"] == "mock"
    assert body["demo_mode"] is True
    _reset_factory_cache()
