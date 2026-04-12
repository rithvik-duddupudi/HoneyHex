from __future__ import annotations

import json
from typing import Any


def llm_tone_audit(*, text: str, model: str) -> dict[str, Any] | None:
    """
    Optional tone / safety pass via LiteLLM. Returns None if [llm] is not installed.
    Requires provider API keys (e.g. OPENAI_API_KEY) when a hosted model is used.
    """
    try:
        import litellm
    except ImportError:
        return None
    if not text.strip():
        return {"skipped": True, "reason": "empty text"}
    prompt = (
        "Classify the following assistant/agent scratch text in one JSON object "
        "with keys: tone (one of: neutral, aggressive, unsafe, personal_data), "
        "confidence (0-1), notes (short string). Text:\n\n"
        f"{text[:8000]}"
    )
    resp = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=200,
    )
    raw = resp.choices[0].message.content or ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw": raw, "parse_error": True}
    return {"model": model, "result": data}
