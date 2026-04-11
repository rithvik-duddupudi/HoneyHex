from __future__ import annotations

from pydantic import BaseModel, Field


class ValidatorVerdict(BaseModel):
    """Structured output from an LLM validator (LLM-Raft / quorum)."""

    model_config = {"extra": "forbid"}

    approved: bool = Field(description="Whether the proposal passes validation.")
    reason: str = Field(default="", description="Short justification.")
