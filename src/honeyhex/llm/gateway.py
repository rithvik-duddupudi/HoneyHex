from __future__ import annotations

import os
from typing import Any

from honeyhex.llm.schemas import ValidatorVerdict


def _extract_message_content(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices")
    if not choices:
        msg = "LLM response has no choices"
        raise ValueError(msg)
    first = choices[0]
    message = getattr(first, "message", None) or (
        first.get("message") if isinstance(first, dict) else None
    )
    if message is None:
        msg = "LLM choice has no message"
        raise ValueError(msg)
    content = getattr(message, "content", None) or (
        message.get("content") if isinstance(message, dict) else None
    )
    if content is None:
        msg = "LLM message has no content"
        raise ValueError(msg)
    return str(content).strip()


class LlmGateway:
    """Thin LiteLLM wrapper: all model calls go through here (Phase 7)."""

    def __init__(self, *, default_model: str | None = None) -> None:
        self.default_model = default_model or os.environ.get(
            "HONEYHEX_DEFAULT_MODEL",
            "gpt-4o-mini",
        )

    def complete_validator_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> ValidatorVerdict:
        try:
            import litellm
        except ImportError as e:
            msg = "Install LLM extras: pip install 'honeyhex[llm]'"
            raise ImportError(msg) from e

        use_model = model or self.default_model
        kwargs: dict[str, Any] = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
        }
        # JSON mode when supported (ignored by many providers if unsupported).
        kwargs["response_format"] = {"type": "json_object"}

        response = litellm.completion(**kwargs)
        raw = _extract_message_content(response)
        return ValidatorVerdict.model_validate_json(raw)
