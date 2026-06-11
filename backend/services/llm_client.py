"""All LLM calls go through here. Only this file imports the `anthropic` SDK (spec §12.7).

- complete():      plain text completion
- complete_json(): structured JSON via tool-use, validated against a Pydantic schema,
                   with one "fix this JSON" retry on validation failure
- 3 transport retries with exponential backoff starting at 2s
"""
import json
import time

import anthropic
from pydantic import BaseModel, ValidationError


class LLMError(Exception):
    """Raised when the LLM call ultimately fails — message is safe to show users."""


class LLMClient:
    MAX_RETRIES = 3
    BACKOFF_START_SECONDS = 2

    def __init__(self, api_key: str, model_id: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model_id = model_id

    def _create(self, **kwargs):
        """messages.create with retry/backoff on transient errors."""
        delay = self.BACKOFF_START_SECONDS
        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return self._client.messages.create(model=self.model_id, **kwargs)
            except (anthropic.APIConnectionError, anthropic.RateLimitError,
                    anthropic.InternalServerError) as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= 2
            except anthropic.AuthenticationError:
                raise LLMError("API key was rejected by Anthropic — check Settings.")
            except anthropic.APIStatusError as e:
                raise LLMError(f"AI provider error (HTTP {e.status_code}).")
        raise LLMError(f"AI provider unreachable after {self.MAX_RETRIES} attempts: {type(last_error).__name__}")

    def complete(self, messages: list[dict], max_tokens: int = 4096, system: str | None = None) -> str:
        kwargs: dict = {"messages": messages, "max_tokens": max_tokens}
        if system:
            kwargs["system"] = system
        response = self._create(**kwargs)
        return "".join(block.text for block in response.content if block.type == "text")

    def complete_json(
        self,
        messages: list[dict],
        schema: type[BaseModel],
        max_tokens: int = 8192,
        system: str | None = None,
    ) -> BaseModel:
        """Force JSON output by exposing the Pydantic schema as a tool the model must call."""
        tool = {
            "name": "submit_result",
            "description": "Submit the structured result matching the required schema.",
            "input_schema": schema.model_json_schema(),
        }
        kwargs: dict = {
            "messages": messages,
            "max_tokens": max_tokens,
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": "submit_result"},
        }
        if system:
            kwargs["system"] = system

        response = self._create(**kwargs)
        raw = self._tool_input(response)

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
                        f"{first_error}\n\nCall submit_result again with corrected JSON."
                    ),
                },
            ]
            kwargs["messages"] = repair_messages
            response = self._create(**kwargs)
            raw = self._tool_input(response)
            try:
                return schema.model_validate(raw)
            except ValidationError:
                raise LLMError("AI output failed validation twice — try Generate again.")

    @staticmethod
    def _tool_input(response) -> dict:
        for block in response.content:
            if block.type == "tool_use":
                return block.input
        raise LLMError("AI response contained no structured output.")
