from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class StateDiff(BaseModel):
    """Snapshot delta for a Think-to-Act cycle (prompt, context, scratchpad, tools)."""

    model_config = {"extra": "forbid"}

    prompt: str = ""
    rag_context: str = ""
    scratchpad: str = ""
    tool_outputs: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str = ""
    task: str = ""
    model: str = ""


class ThoughtCommit(BaseModel):
    """Immutable thought-commit record; maps to one Git commit in `.honeyhex/`."""

    model_config = {"extra": "forbid"}

    commit_hash: str
    parent_hash: str | None
    internal_monologue: str
    diff: StateDiff
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


def payload_relative_path() -> str:
    """Tracked path inside the HoneyHex git working tree."""
    return "thoughts/snapshot.json"
