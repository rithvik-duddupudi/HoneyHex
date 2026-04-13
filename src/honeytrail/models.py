# src/honeytrail/models.py
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

TrailNodeKind = Literal["thought", "tool", "fork", "merge", "compact"]


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class TrailNode(BaseModel):
    id: str
    session_id: str
    parent_id: str | None
    kind: TrailNodeKind
    summary: str = ""
    monologue: str = ""
    state_json: str = "{}"
    tool_name: str | None = None
    tool_input_json: str | None = None
    tool_output_summary: str | None = None
    branch_label: str | None = None
    merge_parent_b_id: str | None = None
    created_at: str


class RollbackResult(BaseModel):
    previous_head_id: str | None
    new_head_id: str | None
