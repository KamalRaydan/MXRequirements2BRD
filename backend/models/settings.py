"""Request/response schemas for settings routes (spec §10.4)."""
from pydantic import BaseModel


class ProviderInfo(BaseModel):
    key: str               # "anthropic" | "openai"
    label: str             # "Anthropic Claude"
    default_model: str
    models_url: str        # docs page listing available model names
    configured: bool       # True when an API key for this provider is in the Keychain


class ProviderOut(BaseModel):
    provider: str          # currently selected provider
    model_id: str
    configured: bool       # key exists for the selected provider
    providers: list[ProviderInfo]


class ProviderIn(BaseModel):
    provider: str
    model_id: str


class ApiKeyIn(BaseModel):
    provider: str
    api_key: str


class ProviderTestIn(BaseModel):
    """Test Connection payload — all optional; falls back to saved settings/Keychain.

    api_key lets the UI test a freshly typed key without saving it first.
    """

    provider: str | None = None
    model_id: str | None = None
    api_key: str | None = None
