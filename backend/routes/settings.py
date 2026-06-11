"""Provider settings + API key management (spec §10.4). The key goes straight
to the macOS Keychain and is never persisted or logged anywhere else."""
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ProviderSettings
from models.settings import ApiKeyIn, ProviderIn, ProviderOut
from routes import api_error
from services import keystore
from services.llm_client import LLMClient, LLMError

router = APIRouter()


def _get_or_create(db: Session) -> ProviderSettings:
    settings = db.get(ProviderSettings, 1)
    if not settings:
        settings = ProviderSettings(id=1, provider="anthropic", model_id="claude-sonnet-4-6")
        db.add(settings)
        db.commit()
    return settings


@router.get("/settings/provider", response_model=ProviderOut)
def get_provider(db: Session = Depends(get_db)):
    settings = _get_or_create(db)
    return ProviderOut(
        provider=settings.provider,
        model_id=settings.model_id,
        configured=keystore.is_configured(),
    )


@router.post("/settings/provider", response_model=ProviderOut)
def set_provider(body: ProviderIn, db: Session = Depends(get_db)):
    if body.provider != "anthropic":
        raise api_error(422, "PROVIDER_NOT_AVAILABLE",
                        "Only Anthropic Claude is available in this version")
    settings = _get_or_create(db)
    settings.provider = body.provider
    settings.model_id = body.model_id
    db.commit()
    return ProviderOut(provider=settings.provider, model_id=settings.model_id,
                       configured=keystore.is_configured())


@router.post("/settings/api-key")
def set_api_key(body: ApiKeyIn):
    if not body.api_key.strip():
        raise api_error(422, "EMPTY_KEY", "API key cannot be empty")
    keystore.set_api_key(body.api_key.strip())
    return {"success": True}


@router.delete("/settings/api-key")
def delete_api_key():
    keystore.delete_api_key()
    return {"success": True}


@router.post("/settings/provider/test")
def test_provider(db: Session = Depends(get_db)):
    api_key = keystore.get_api_key()
    if not api_key:
        raise api_error(400, "NO_KEY", "No API key configured — save one first")
    settings = _get_or_create(db)
    started = time.monotonic()
    try:
        llm = LLMClient(api_key=api_key, model_id=settings.model_id)
        llm.complete(messages=[{"role": "user", "content": "Reply OK"}], max_tokens=8)
    except LLMError as e:
        raise api_error(400, "TEST_FAILED", str(e))
    return {"success": True, "latency_ms": int((time.monotonic() - started) * 1000)}
