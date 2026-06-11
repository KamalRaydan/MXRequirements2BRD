"""Stage 2a — compress oversized sources before analysis (spec §12.3)."""
import config
from models.pipeline import ExtractedSource, SummarizedSource
from services.llm_client import LLMClient


def _load_prompt() -> str:
    return (config.PROMPTS_DIR / "summarizer.txt").read_text(encoding="utf-8")


def summarize_if_needed(llm: LLMClient, source: ExtractedSource) -> SummarizedSource:
    if source.char_count <= config.TOKEN_THRESHOLD:
        return SummarizedSource(
            source_id=source.source_id,
            filename=source.filename,
            timestamp=source.timestamp,
            content=source.raw_text,
            was_summarized=False,
        )

    prompt = _load_prompt().format(
        filename=source.filename,
        timestamp=source.timestamp.isoformat(),
    )
    summary = llm.complete(
        messages=[{"role": "user", "content": f"{prompt}\n\nSOURCE MATERIAL:\n{source.raw_text}"}],
        max_tokens=config.LLM_MAX_TOKENS_SUMMARIZE,
    )
    return SummarizedSource(
        source_id=source.source_id,
        filename=source.filename,
        timestamp=source.timestamp,
        content=summary,
        was_summarized=True,
    )
