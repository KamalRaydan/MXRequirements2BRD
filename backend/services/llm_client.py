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
import time
from pathlib import Path

import anthropic
import openai
from pydantic import BaseModel, ValidationError

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


class LLMClient:
    MAX_RETRIES = 3
    BACKOFF_START_SECONDS = 2

    def __init__(self, api_key: str, model_id: str, provider: str = "anthropic"):
        self.provider = provider
        self.model_id = model_id
        if provider == "anthropic":
            self._anthropic = anthropic.Anthropic(api_key=api_key)
        elif provider == "openai":
            self._openai = openai.OpenAI(api_key=api_key)
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

    def complete(self, messages: list[dict], max_tokens: int = 4096, system: str | None = None) -> str:
        if self.provider == "anthropic":
            kwargs: dict = {"model": self.model_id, "messages": messages, "max_tokens": max_tokens}
            if system:
                kwargs["system"] = system
            response = self._with_retries(lambda: self._anthropic.messages.create(**kwargs))
            return "".join(block.text for block in response.content if block.type == "text")

        oa_messages = ([{"role": "system", "content": system}] if system else []) + messages
        response = self._with_retries(lambda: self._openai.chat.completions.create(
            model=self.model_id, messages=oa_messages, max_completion_tokens=max_tokens,
        ))
        return response.choices[0].message.content or ""

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
    ) -> BaseModel:
        raw = self._json_request(messages, schema, max_tokens, system)
        try:
            return schema.model_validate(raw)
        except ValidationError as first_error:
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
            raw = self._json_request(repair_messages, schema, max_tokens, system)
            try:
                return schema.model_validate(raw)
            except ValidationError:
                raise LLMError("AI output failed validation twice — try Generate again.")

    def _json_request(self, messages, schema, max_tokens, system) -> dict:
        """One JSON-producing call, provider-specific."""
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
                kwargs["system"] = system
            response = self._with_retries(lambda: self._anthropic.messages.create(**kwargs))
            for block in response.content:
                if block.type == "tool_use":
                    return block.input
            raise LLMError("AI response contained no structured output.")

        # OpenAI: JSON mode + schema embedded in the system message (spec §12.7)
        json_system = (
            (system + "\n\n" if system else "")
            + "Respond with a single JSON object that matches this JSON schema exactly:\n"
            + json.dumps(schema.model_json_schema())
        )
        oa_messages = [{"role": "system", "content": json_system}] + messages
        response = self._with_retries(lambda: self._openai.chat.completions.create(
            model=self.model_id,
            messages=oa_messages,
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"},
        ))
        content = response.choices[0].message.content or ""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            raise LLMError("AI response was not valid JSON.")
