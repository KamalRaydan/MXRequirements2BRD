"""Request/response schemas for settings routes (spec §10.4)."""
from pydantic import BaseModel


class ProviderOut(BaseModel):
    provider: str
    model_id: str
    configured: bool  # True when an API key exists in the Keychain


class ProviderIn(BaseModel):
    provider: str
    model_id: str


class ApiKeyIn(BaseModel):
    api_key: str
