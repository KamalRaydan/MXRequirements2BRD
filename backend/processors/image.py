"""Image → text via the configured AI provider's vision endpoint (spec §18, M5).

The one exception to "only extracted text goes to the LLM": the image bytes go
to the user's chosen provider (Claude / GPT-4o) for OCR + description, and only
the returned text enters the pipeline. Raw media is never sent anywhere else.
"""
import config
from db.database import SessionLocal
from db.models import ProviderSettings
from services import keystore
from services.llm_client import LLMClient


def extract(filepath: str) -> str:
    db = SessionLocal()
    try:
        settings = db.get(ProviderSettings, 1)
    finally:
        db.close()
    provider = settings.provider if settings else "anthropic"
    model_id = settings.model_id if settings else config.PROVIDERS[provider]["default_model"]

    api_key = keystore.get_api_key(provider)
    if not api_key:
        raise ValueError(
            "Reading images uses your AI provider — save an API key in Settings, then press Retry"
        )
    return LLMClient(api_key=api_key, model_id=model_id, provider=provider).describe_image(filepath)
