"""All LLM calls go through here. Only this file imports the `anthropic` and
`openai` SDKs (spec §12.7).

- complete():       plain text completion
- complete_json():  structured JSON validated against a Pydantic schema, with one
                    "fix this JSON" retry on validation failure.
                    Anthropic: forced tool-use carrying the schema.
                    OpenAI: response_format=json_object + schema in the system message.
- describe_image(): image → OCR + description text (Milestone 5 vision path)
- 3 transport retries with exponential backoff starting at 2s (both providers)
"""
import base64
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

import anthropic
import openai
from pydantic import BaseModel, ValidationError

import config

# Server-side diagnostics. Logged at WARNING/ERROR so they appear in the uvicorn
# terminal (e.g. the window running `npm run app`) without extra logging config.
logger = logging.getLogger("maximobrd.llm")

# Both SDKs use the same exception class names, so retry handling is shared
_TRANSIENT_ERRORS = (
    anthropic.APIConnectionError, anthropic.InternalServerError,
    openai.APIConnectionError, openai.InternalServerError,
)
_RATE_LIMIT_ERRORS = (anthropic.RateLimitError, openai.RateLimitError)
_AUTH_ERRORS = (anthropic.AuthenticationError, openai.AuthenticationError)
_STATUS_ERRORS = (anthropic.APIStatusError, openai.APIStatusError)

# Where to fix billing/credit problems, per provider
_BILLING_HINTS = {
    "openai": "platform.openai.com → Settings → Billing (API credits are separate from ChatGPT Plus)",
    "anthropic": "console.anthropic.com → Billing",
}


class LLMError(Exception):
    """Raised when the LLM call ultimately fails — message is safe to show users."""


# How often a streaming call reports progress back to the caller, measured in
# characters received. Char-based (not chunk-based) so the heartbeat fires reliably
# regardless of how the provider chunks the stream — keeps the UI moving without
# flooding the bus.
_PROGRESS_EVERY_CHARS = 800

# stop_reason values that mean the model finished normally. Anything else (most
# importantly "max_tokens") means the output is incomplete.
_NORMAL_STOP_REASONS = {"end_turn", "tool_use", "stop_sequence"}


def _check_truncation(stop_reason: str | None, max_tokens: int, fatal: bool) -> None:
    """Log (and for JSON calls, raise on) a response that didn't finish cleanly.
    `fatal=True` is used for structured-JSON calls, where a truncated response is
    invalid JSON and there's no point retrying schema validation against it."""
    if stop_reason in _NORMAL_STOP_REASONS or stop_reason is None:
        return
    logger.warning("LLM response stop_reason=%s (max_tokens=%s)", stop_reason, max_tokens)
    if fatal and stop_reason == "max_tokens":
        raise LLMError(
            f"The AI hit its output length limit ({max_tokens} tokens) before finishing, "
            "so the result came back incomplete. Try generating from a smaller batch of "
            "sources, or raise the matching LLM_MAX_TOKENS_* setting."
        )


class LLMClient:
    MAX_RETRIES = 3
    BACKOFF_START_SECONDS = 2

    def __init__(self, api_key: str, model_id: str, provider: str = "anthropic",
                 timeout: float | None = None):
        self.provider = provider
        self.model_id = model_id
        # An explicit timeout replaces the SDK default (~10 min). Paired with
        # streaming, it only fires when the connection genuinely stalls.
        self.timeout = config.LLM_TIMEOUT_SECONDS if timeout is None else timeout
        if provider == "anthropic":
            self._anthropic = anthropic.Anthropic(api_key=api_key, timeout=self.timeout)
        elif provider == "openai":
            self._openai = openai.OpenAI(api_key=api_key, timeout=self.timeout)
        else:
            raise LLMError(f"Unknown AI provider '{provider}'")

    # ---- shared retry wrapper ----

    def _with_retries(self, request_fn):
        delay = self.BACKOFF_START_SECONDS
        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return request_fn()
            except _AUTH_ERRORS:
                raise LLMError("API key was rejected by the provider — check Settings.")
            except _RATE_LIMIT_ERRORS as e:
                # OpenAI reports "no credits on the account" as a 429 too —
                # that's a billing problem, not a rate problem; never retry it
                if "insufficient_quota" in str(e):
                    raise LLMError(
                        "Your account has no available API credits (insufficient_quota). "
                        f"Add credits at {_BILLING_HINTS.get(self.provider, 'your provider billing page')}."
                    )
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= 2
            except _TRANSIENT_ERRORS as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= 2
            except _STATUS_ERRORS as e:
                raise LLMError(f"AI provider error (HTTP {e.status_code}).")

        if isinstance(last_error, _RATE_LIMIT_ERRORS):
            raise LLMError(f"Rate limited by the AI provider after {self.MAX_RETRIES} attempts — "
                           "wait a minute and try again.")
        raise LLMError(f"AI provider unreachable after {self.MAX_RETRIES} attempts: {type(last_error).__name__}")

    # ---- plain text ----

    def complete(self, messages: list[dict], max_tokens: int = 4096,
                 system: str | None = None,
                 on_progress: Callable[[int], None] | None = None) -> str:
        """Plain-text completion. Streams the response so large outputs don't trip the
        request timeout, and calls on_progress(chars_received) periodically so callers
        can show a live heartbeat."""
        if self.provider == "anthropic":
            kwargs: dict = {"model": self.model_id, "messages": messages, "max_tokens": max_tokens}
            if system:
                kwargs["system"] = system
            return self._with_retries(lambda: self._anthropic_stream_text(kwargs, on_progress))

        oa_messages = ([{"role": "system", "content": system}] if system else []) + messages
        return self._with_retries(lambda: self._openai_stream_text(oa_messages, max_tokens, on_progress))

    # ---- streaming helpers (one full stream per call; retried as a unit) ----

    def _anthropic_stream_text(self, kwargs: dict, on_progress) -> str:
        chunks: list[str] = []
        received = last_reported = 0
        with self._anthropic.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                chunks.append(text)
                received += len(text)
                if on_progress and received - last_reported >= _PROGRESS_EVERY_CHARS:
                    last_reported = received
                    on_progress(received)
            message = stream.get_final_message()
        # A truncated summary is still usable, so warn but don't fail (fatal=False).
        _check_truncation(getattr(message, "stop_reason", None), kwargs.get("max_tokens", 0), fatal=False)
        return "".join(block.text for block in message.content if block.type == "text")

    def _openai_stream_text(self, oa_messages: list[dict], max_tokens: int, on_progress) -> str:
        stream = self._openai.chat.completions.create(
            model=self.model_id, messages=oa_messages,
            max_completion_tokens=max_tokens, stream=True,
        )
        chunks: list[str] = []
        received = last_reported = 0
        finish_reason = None
        for chunk in stream:
            if not chunk.choices:
                continue
            finish_reason = chunk.choices[0].finish_reason or finish_reason
            delta = chunk.choices[0].delta.content
            if delta:
                chunks.append(delta)
                received += len(delta)
                if on_progress and received - last_reported >= _PROGRESS_EVERY_CHARS:
                    last_reported = received
                    on_progress(received)
        # OpenAI reports truncation as finish_reason="length"
        _check_truncation("max_tokens" if finish_reason == "length" else finish_reason, max_tokens, fatal=False)
        return "".join(chunks)

    # ---- image → text (vision, Milestone 5) ----

    _IMAGE_MEDIA_TYPES = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    }

    VISION_PROMPT = (
        "This image is a source document for business requirements gathering — for example "
        "a whiteboard photo, presentation slide, screenshot, or scanned page. Transcribe ALL "
        "readable text exactly as written, then briefly describe any diagrams, tables, or "
        "annotations and what they convey. Respond with plain text only."
    )

    def describe_image(self, filepath: str, max_tokens: int = 4096) -> str:
        media_type = self._IMAGE_MEDIA_TYPES.get(Path(filepath).suffix.lower())
        if not media_type:
            raise LLMError(f"Unsupported image format '{Path(filepath).suffix}'")
        data = base64.standard_b64encode(Path(filepath).read_bytes()).decode()

        if self.provider == "anthropic":
            message = {"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                {"type": "text", "text": self.VISION_PROMPT},
            ]}
            response = self._with_retries(lambda: self._anthropic.messages.create(
                model=self.model_id, messages=[message], max_tokens=max_tokens,
            ))
            return "".join(block.text for block in response.content if block.type == "text")

        message = {"role": "user", "content": [
            {"type": "text", "text": self.VISION_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}},
        ]}
        response = self._with_retries(lambda: self._openai.chat.completions.create(
            model=self.model_id, messages=[message], max_completion_tokens=max_tokens,
        ))
        return response.choices[0].message.content or ""

    # ---- structured JSON ----

    def complete_json(
        self,
        messages: list[dict],
        schema: type[BaseModel],
        max_tokens: int = 8192,
        system: str | None = None,
        on_progress: Callable[[int], None] | None = None,
        cache_system: bool = False,
    ) -> BaseModel:
        # cache_system caches the (large, reused) system+tool prefix on Anthropic so
        # repeated batch calls only pay ~10% for it (spec: map-reduce analysis).
        raw = self._json_request(messages, schema, max_tokens, system, on_progress, cache_system)
        try:
            return schema.model_validate(raw)
        except ValidationError as first_error:
            # Surface what actually went wrong (field, expected vs. got) in the server
            # log — the user-facing message stays generic per spec §10.
            logger.warning(
                "%s validation failed (attempt 1), retrying. Errors:\n%s\nRaw output (first 1000 chars): %s",
                schema.__name__, first_error, json.dumps(raw)[:1000],
            )
            # One repair pass: show the model its own output + the validation errors
            repair_messages = messages + [
                {"role": "assistant", "content": f"Previous JSON output:\n{json.dumps(raw)}"},
                {
                    "role": "user",
                    "content": (
                        "That JSON failed schema validation with these errors:\n"
                        f"{first_error}\n\nReturn corrected JSON matching the schema."
                    ),
                },
            ]
            raw = self._json_request(repair_messages, schema, max_tokens, system, on_progress, cache_system)
            try:
                return schema.model_validate(raw)
            except ValidationError as second_error:
                logger.error(
                    "%s validation failed twice — giving up. Errors:\n%s\nRaw output (first 1000 chars): %s",
                    schema.__name__, second_error, json.dumps(raw)[:1000],
                )
                raise LLMError(
                    "AI output failed validation twice — try Generate again. "
                    "(See the app's terminal logs for the exact validation error.)"
                )

    def _json_request(self, messages, schema, max_tokens, system, on_progress=None,
                      cache_system: bool = False) -> dict:
        """One JSON-producing call, provider-specific. Streamed so big results don't
        trip the request timeout; reports progress by JSON characters received."""
        if self.provider == "anthropic":
            # Force JSON by exposing the schema as a tool the model must call
            tool = {
                "name": "submit_result",
                "description": "Submit the structured result matching the required schema.",
                "input_schema": schema.model_json_schema(),
            }
            kwargs: dict = {
                "model": self.model_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "tools": [tool],
                "tool_choice": {"type": "tool", "name": "submit_result"},
            }
            if system:
                # A cache_control marker on the system block caches the whole reused
                # prefix (tool schema + system text), so back-to-back batch calls read
                # it at ~10% cost instead of re-paying full price each time.
                kwargs["system"] = (
                    [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
                    if cache_system else system
                )
            return self._with_retries(lambda: self._anthropic_stream_json(kwargs, on_progress))

        # OpenAI: JSON mode + schema embedded in the system message (spec §12.7)
        json_system = (
            (system + "\n\n" if system else "")
            + "Respond with a single JSON object that matches this JSON schema exactly:\n"
            + json.dumps(schema.model_json_schema())
        )
        oa_messages = [{"role": "system", "content": json_system}] + messages
        return self._with_retries(lambda: self._openai_stream_json(oa_messages, max_tokens, on_progress))

    def _anthropic_stream_json(self, kwargs: dict, on_progress) -> dict:
        received = last_reported = 0
        with self._anthropic.messages.stream(**kwargs) as stream:
            for event in stream:
                # tool-use JSON arrives as input_json_delta events. Read the delta
                # defensively (by attribute, not event.type) so the heartbeat fires
                # regardless of how this SDK version labels the events.
                delta = getattr(event, "delta", None)
                piece = getattr(delta, "partial_json", None) or getattr(delta, "text", None)
                if piece:
                    received += len(piece)
                    if on_progress and received - last_reported >= _PROGRESS_EVERY_CHARS:
                        last_reported = received
                        on_progress(received)
            message = stream.get_final_message()
        # Raise a clear error if the JSON was cut off mid-stream by the token limit.
        _check_truncation(getattr(message, "stop_reason", None), kwargs.get("max_tokens", 0), fatal=True)
        for block in message.content:
            if block.type == "tool_use":
                return block.input
        raise LLMError("AI response contained no structured output.")

    def _openai_stream_json(self, oa_messages: list[dict], max_tokens: int, on_progress) -> dict:
        stream = self._openai.chat.completions.create(
            model=self.model_id,
            messages=oa_messages,
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"},
            stream=True,
        )
        chunks: list[str] = []
        received = last_reported = 0
        finish_reason = None
        for chunk in stream:
            if not chunk.choices:
                continue
            finish_reason = chunk.choices[0].finish_reason or finish_reason
            delta = chunk.choices[0].delta.content
            if delta:
                chunks.append(delta)
                received += len(delta)
                if on_progress and received - last_reported >= _PROGRESS_EVERY_CHARS:
                    last_reported = received
                    on_progress(received)
        _check_truncation("max_tokens" if finish_reason == "length" else finish_reason, max_tokens, fatal=True)
        content = "".join(chunks)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error("OpenAI JSON parse failed; first 500 chars: %s", content[:500])
            raise LLMError("AI response was not valid JSON.")
