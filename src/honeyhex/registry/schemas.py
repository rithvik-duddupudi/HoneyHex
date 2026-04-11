from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from honeyhex.llm.schemas import ValidatorVerdict


class SwarmOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    name: str
    quorum_threshold: float
    validator_agent_ids: list[str]


class AgentOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    swarm_id: str
    display_name: str | None
    last_head_sha: str | None
    branch: str | None
    updated_at: datetime


class PullRequestCreate(BaseModel):
    model_config = {"extra": "forbid"}

    swarm_id: str = "default"
    source_agent_id: str
    target_agent_id: str
    head_sha: str
    title: str = ""


class PullRequestOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    swarm_id: str
    source_agent_id: str
    target_agent_id: str
    head_sha: str
    title: str
    status: str
    votes: dict[str, bool]
    created_at: datetime


class VoteIn(BaseModel):
    model_config = {"extra": "forbid"}

    validator_id: str
    approved: bool


class StatusResponse(BaseModel):
    model_config = {"extra": "forbid"}

    swarm: SwarmOut
    agents: list[AgentOut]
    open_pull_requests: list[PullRequestOut]


class BlackboardAppend(BaseModel):
    model_config = {"extra": "forbid"}

    swarm_id: str = "default"
    agent_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class BlackboardEntryOut(BaseModel):
    model_config = {"extra": "forbid"}

    id: int
    swarm_id: str
    agent_id: str
    lamport: int
    payload: dict[str, Any]
    created_at: datetime


class LlmEvaluateIn(BaseModel):
    model_config = {"extra": "forbid"}

    model: str = "gpt-4o-mini"
    validator_id: str = "validator-a"


class LlmEvaluateOut(BaseModel):
    model_config = {"extra": "forbid"}

    verdict: ValidatorVerdict
    pull_request: PullRequestOut
