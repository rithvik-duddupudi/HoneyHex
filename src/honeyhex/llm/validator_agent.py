from __future__ import annotations

import json
from typing import Any

from honeyhex.llm.gateway import LlmGateway
from honeyhex.llm.schemas import ValidatorVerdict

_SYSTEM = (
    "You are a HoneyHex validator agent. Given a pull request summary as JSON, "
    "decide if it is safe to merge from a systems perspective (no secrets leaked, "
    "coherent metadata). Respond with JSON only: "
    '{"approved": <bool>, "reason": "<short string>"}'
)


def evaluate_pull_request_dict(
    pr: dict[str, Any],
    *,
    model: str | None = None,
    gateway: LlmGateway | None = None,
) -> ValidatorVerdict:
    """Run a lightweight validator LLM over PR metadata (Proposer/Validator pattern)."""
    gw = gateway or LlmGateway()
    user = json.dumps({"pull_request": pr}, indent=2)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ]
    return gw.complete_validator_json(messages, model=model)
