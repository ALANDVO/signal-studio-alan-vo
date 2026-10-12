import pytest
import httpx
from app.services.llm_client import dispatch_llm_request, sanitize_error_message


@pytest.mark.asyncio
async def test_offline_deterministic_fallback_when_no_api_key(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.LLM_API_KEY", None)
    monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "openai-compatible")

    messages = [{"role": "user", "content": "Analyze system requirements."}]
    result = await dispatch_llm_request(messages)

    assert result.is_offline_fallback is True
    assert result.provider == "offline-deterministic"
    assert "[Offline Advisory Mode]" in result.content


@pytest.mark.asyncio
async def test_mocked_openai_provider_call(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.LLM_API_KEY", "synthetic_test_key_00000000")
    monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "openai-compatible")
    monkeypatch.setattr("app.core.config.settings.LLM_BASE_URL", "http://mock-llm.local/v1")

    async def mock_post(self, url, headers=None, json=None):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Mocked OpenAI reply", "reasoning_content": "Mocked thought"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    messages = [{"role": "user", "content": "Test prompt"}]
    result = await dispatch_llm_request(messages, provider="openai-compatible")

    assert result.content == "Mocked OpenAI reply"
    assert result.reasoning == "Mocked thought"
    assert result.is_offline_fallback is False


@pytest.mark.asyncio
async def test_mocked_anthropic_provider_call(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.LLM_API_KEY", "synthetic_test_key_00000000")
    monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "anthropic")
    monkeypatch.setattr("app.core.config.settings.LLM_BASE_URL", "http://mock-anthropic.local")

    async def mock_post(self, url, headers=None, json=None):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "Mocked Anthropic reply"}],
                "usage": {"input_tokens": 8, "output_tokens": 4},
            },
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    messages = [{"role": "user", "content": "Hello Anthropic"}]
    result = await dispatch_llm_request(messages, provider="anthropic")
    assert result.content == "Mocked Anthropic reply"


def test_sanitize_error_message():
    raw_error = "Error connecting with Bearer synthetic_secret_token_12345 at key=secret_555"
    sanitized = sanitize_error_message(raw_error)
    assert "synthetic_secret_token_12345" not in sanitized
    assert "[REDACTED]" in sanitized
