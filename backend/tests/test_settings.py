"""Provider settings routes accept both providers and never touch the real Keychain."""
import pytest
from fastapi.testclient import TestClient

import main
from services import keystore


@pytest.fixture
def client(monkeypatch):
    # Fake in-memory keystore so tests never touch the macOS Keychain
    fake_store: dict[str, str] = {}
    monkeypatch.setattr(keystore, "set_api_key", lambda p, v: fake_store.__setitem__(p, v))
    monkeypatch.setattr(keystore, "get_api_key", lambda p: fake_store.get(p))
    monkeypatch.setattr(keystore, "delete_api_key", lambda p: fake_store.pop(p, None))
    monkeypatch.setattr(keystore, "is_configured", lambda p: p in fake_store)
    with TestClient(main.app) as test_client:
        yield test_client


def test_defaults_to_anthropic(client):
    data = client.get("/settings/provider").json()
    assert data["provider"] == "anthropic"
    assert data["configured"] is False
    provider_keys = {p["key"] for p in data["providers"]}
    assert provider_keys == {"anthropic", "openai"}
    # Every provider entry carries a models docs link for the UI
    assert all(p["models_url"].startswith("https://") for p in data["providers"])


def test_switch_to_openai(client):
    response = client.post("/settings/provider", json={"provider": "openai", "model_id": "gpt-4o"})
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["model_id"] == "gpt-4o"


def test_unknown_provider_rejected(client):
    response = client.post("/settings/provider", json={"provider": "gemini", "model_id": "x"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PROVIDER_NOT_AVAILABLE"


def test_connection_test_uses_form_provider_not_saved_one(client, monkeypatch):
    """Regression: saved provider is anthropic, but the user is testing OpenAI
    from the form — the error must reference OpenAI, not Anthropic."""
    response = client.post("/settings/provider/test",
                           json={"provider": "openai", "model_id": "gpt-4o"})
    assert response.status_code == 400
    assert "OpenAI" in response.json()["error"]["message"]
    assert "Anthropic" not in response.json()["error"]["message"]


def test_connection_test_with_unsaved_key(client, monkeypatch):
    """An api_key typed in the form is tested directly, without being stored."""
    captured = {}

    class FakeLLM:
        def __init__(self, api_key, model_id, provider="anthropic"):
            captured.update(api_key=api_key, model_id=model_id, provider=provider)

        def complete(self, messages, max_tokens=4096, system=None):
            return "OK"

    import routes.settings as settings_routes
    monkeypatch.setattr(settings_routes, "LLMClient", FakeLLM)

    response = client.post("/settings/provider/test", json={
        "provider": "openai", "model_id": "gpt-4o", "api_key": "sk-unsaved",
    })
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured == {"api_key": "sk-unsaved", "model_id": "gpt-4o", "provider": "openai"}

    # The typed key was tested but never stored
    assert keystore.get_api_key("openai") is None


def test_per_provider_keys(client):
    client.post("/settings/api-key", json={"provider": "anthropic", "api_key": "sk-ant-x"})
    client.post("/settings/api-key", json={"provider": "openai", "api_key": "sk-oa-y"})

    data = client.get("/settings/provider").json()
    configured = {p["key"]: p["configured"] for p in data["providers"]}
    assert configured == {"anthropic": True, "openai": True}

    # Deleting one provider's key leaves the other intact
    client.delete("/settings/api-key/openai")
    data = client.get("/settings/provider").json()
    configured = {p["key"]: p["configured"] for p in data["providers"]}
    assert configured == {"anthropic": True, "openai": False}
