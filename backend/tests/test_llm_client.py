"""LLMClient retry behavior with mocked provider errors (spec §17.1)."""
import httpx
import openai
import pytest

from services.llm_client import LLMClient, LLMError


def _rate_limit_error(message: str) -> openai.RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return openai.RateLimitError(message, response=response, body=None)


@pytest.fixture
def client(monkeypatch):
    # No sleeping during tests
    import services.llm_client as llm_module
    monkeypatch.setattr(llm_module.time, "sleep", lambda s: None)
    return LLMClient(api_key="test-key", model_id="gpt-4o", provider="openai")


def test_insufficient_quota_fails_fast_with_billing_hint(client):
    """OpenAI returns 429 insufficient_quota when the account has no credits —
    a billing problem, so it must not be retried and the message must say so."""
    calls = {"n": 0}

    def request():
        calls["n"] += 1
        raise _rate_limit_error("Error code: 429 - insufficient_quota: check your plan and billing")

    with pytest.raises(LLMError) as exc:
        client._with_retries(request)

    assert calls["n"] == 1  # no retries — retrying can't fix billing
    assert "credits" in str(exc.value)
    assert "platform.openai.com" in str(exc.value)


def test_real_rate_limit_retries_then_clear_message(client):
    calls = {"n": 0}

    def request():
        calls["n"] += 1
        raise _rate_limit_error("Error code: 429 - rate limit exceeded, slow down")

    with pytest.raises(LLMError) as exc:
        client._with_retries(request)

    assert calls["n"] == 3  # genuine rate limiting is retried
    assert "Rate limited" in str(exc.value)


def test_transient_error_recovers(client):
    """A connection error on attempt 1 followed by success returns the result."""
    calls = {"n": 0}

    def request():
        calls["n"] += 1
        if calls["n"] == 1:
            raise openai.APIConnectionError(
                request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
            )
        return "ok"

    assert client._with_retries(request) == "ok"
    assert calls["n"] == 2
