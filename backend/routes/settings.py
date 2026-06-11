"""Provider settings + API key management (spec §10.4). Keys go straight to the
macOS Keychain (one entry per provider) and are never persisted or logged
anywhere else."""
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import config
from db.database import get_db
from db.models import ProviderSettings
from models.settings import ApiKeyIn, ProviderIn, ProviderInfo, ProviderOut, ProviderTestIn
from routes import api_error
from services import keystore
from services.llm_client import LLMClient, LLMError

router = APIRouter()


def _get_or_create(db: Session) -> ProviderSettings:
    settings = db.get(ProviderSettings, 1)
    if not settings:
        settings = ProviderSettings(id=1, provider="anthropic",
                                    model_id=config.PROVIDERS["anthropic"]["default_model"])
        db.add(settings)
        db.commit()
    return settings


def _provider_out(settings: ProviderSettings) -> ProviderOut:
    return ProviderOut(
        provider=settings.provider,
        model_id=settings.model_id,
        configured=keystore.is_configured(settings.provider),
        providers=[
            ProviderInfo(
                key=key,
                label=info["label"],
                default_model=info["default_model"],
                models_url=info["models_url"],
                configured=keystore.is_configured(key),
            )
            for key, info in config.PROVIDERS.items()
        ],
    )


@router.get("/settings/provider", response_model=ProviderOut)
def get_provider(db: Session = Depends(get_db)):
    return _provider_out(_get_or_create(db))


@router.post("/settings/provider", response_model=ProviderOut)
def set_provider(body: ProviderIn, db: Session = Depends(get_db)):
    if body.provider not in config.PROVIDERS:
        raise api_error(422, "PROVIDER_NOT_AVAILABLE",
                        f"Unknown provider '{body.provider}'")
    settings = _get_or_create(db)
    settings.provider = body.provider
    settings.model_id = body.model_id.strip() or config.PROVIDERS[body.provider]["default_model"]
    db.commit()
    return _provider_out(settings)


@router.post("/settings/api-key")
def set_api_key(body: ApiKeyIn):
    if body.provider not in config.PROVIDERS:
        raise api_error(422, "PROVIDER_NOT_AVAILABLE", f"Unknown provider '{body.provider}'")
    if not body.api_key.strip():
        raise api_error(422, "EMPTY_KEY", "API key cannot be empty")
    keystore.set_api_key(body.provider, body.api_key.strip())
    return {"success": True}


@router.delete("/settings/api-key/{provider}")
def delete_api_key(provider: str):
    if provider not in config.PROVIDERS:
        raise api_error(422, "PROVIDER_NOT_AVAILABLE", f"Unknown provider '{provider}'")
    keystore.delete_api_key(provider)
    return {"success": True}


@router.post("/settings/provider/test")
def test_provider(body: ProviderTestIn | None = None, db: Session = Depends(get_db)):
    settings = _get_or_create(db)

    # Use what the UI currently shows, falling back to saved settings
    provider = (body.provider if body and body.provider else settings.provider)
    if provider not in config.PROVIDERS:
        raise api_error(422, "PROVIDER_NOT_AVAILABLE", f"Unknown provider '{provider}'")

    if body and body.model_id and body.model_id.strip():
        model_id = body.model_id.strip()
    elif provider == settings.provider:
        model_id = settings.model_id
    else:
        model_id = config.PROVIDERS[provider]["default_model"]

    # A freshly typed (unsaved) key wins; otherwise use this provider's Keychain entry
    api_key = (body.api_key.strip() if body and body.api_key and body.api_key.strip()
               else keystore.get_api_key(provider))
    if not api_key:
        raise api_error(400, "NO_KEY",
                        f"No API key for {config.PROVIDERS[provider]['label']} — enter or save one first")

    started = time.monotonic()
    try:
        llm = LLMClient(api_key=api_key, model_id=model_id, provider=provider)
        llm.complete(messages=[{"role": "user", "content": "Reply OK"}], max_tokens=8)
    except LLMError as e:
        raise api_error(400, "TEST_FAILED", str(e))
    return {"success": True, "latency_ms": int((time.monotonic() - started) * 1000)}
