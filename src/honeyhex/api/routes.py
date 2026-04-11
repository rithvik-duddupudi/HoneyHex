from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from honeyhex.registry.db import get_db
from honeyhex.registry.models import Agent, PullRequest, Swarm
from honeyhex.registry.schemas import (
    AgentOut,
    BlackboardAppend,
    BlackboardEntryOut,
    LlmEvaluateIn,
    LlmEvaluateOut,
    PullRequestCreate,
    PullRequestOut,
    StatusResponse,
    SwarmOut,
    VoteIn,
)
from honeyhex.registry.service import (
    append_blackboard,
    cast_votes_to_bool,
    create_pull_request,
    list_blackboard,
    merge_if_quorum,
    record_vote,
    reject_pr,
    upsert_agent,
)
from honeyhex.registry.service import ensure_swarm as ensure_swarm_svc

router = APIRouter()


def _maybe_publish_pr_event(pr: PullRequest) -> None:
    url = os.environ.get("HONEYHEX_REDIS_URL")
    if not url:
        return
    ch = os.environ.get("HONEYHEX_CHANNEL", "honeyhex:mesh")
    try:
        from honeyhex.mesh.publish import announce_pr_created
    except ImportError:
        return
    announce_pr_created(
        url,
        ch,
        pr_id=pr.id,
        source_agent=pr.source_agent_id,
        target_agent=pr.target_agent_id,
        head_sha=pr.head_sha,
    )


def _pr_out(pr: PullRequest) -> PullRequestOut:
    return PullRequestOut(
        id=pr.id,
        swarm_id=pr.swarm_id,
        source_agent_id=pr.source_agent_id,
        target_agent_id=pr.target_agent_id,
        head_sha=pr.head_sha,
        title=pr.title,
        status=pr.status,
        votes=cast_votes_to_bool(pr.votes or {}),
        created_at=pr.created_at,
    )


def _pr_as_dict(pr: PullRequest) -> dict[str, Any]:
    return {
        "id": pr.id,
        "swarm_id": pr.swarm_id,
        "source_agent_id": pr.source_agent_id,
        "target_agent_id": pr.target_agent_id,
        "head_sha": pr.head_sha,
        "title": pr.title,
        "status": pr.status,
    }


@router.get("/prs/{pr_id}", response_model=PullRequestOut)
def get_pull_request(
    pr_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> PullRequestOut:
    pr = session.get(PullRequest, pr_id)
    if pr is None:
        raise HTTPException(status_code=404, detail="pull request not found")
    return _pr_out(pr)


@router.post("/prs", response_model=PullRequestOut)
def create_pr(
    body: PullRequestCreate,
    session: Annotated[Session, Depends(get_db)],
) -> PullRequestOut:
    pr = create_pull_request(
        session,
        swarm_id=body.swarm_id,
        source_agent_id=body.source_agent_id,
        target_agent_id=body.target_agent_id,
        head_sha=body.head_sha,
        title=body.title,
    )
    _maybe_publish_pr_event(pr)
    return _pr_out(pr)


@router.post("/prs/{pr_id}/llm-evaluate", response_model=LlmEvaluateOut)
def llm_evaluate_pull_request(
    pr_id: str,
    body: LlmEvaluateIn,
    session: Annotated[Session, Depends(get_db)],
) -> LlmEvaluateOut:
    from honeyhex.llm.validator_agent import evaluate_pull_request_dict

    pr = session.get(PullRequest, pr_id)
    if pr is None:
        raise HTTPException(status_code=404, detail="pull request not found")
    if pr.status != "open":
        raise HTTPException(status_code=400, detail="pull request is not open")
    payload = _pr_as_dict(pr)
    try:
        verdict = evaluate_pull_request_dict(payload, model=body.model)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"llm error: {e}") from e
    try:
        record_vote(session, pr_id, body.validator_id, verdict.approved)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    pr2 = session.get(PullRequest, pr_id)
    if pr2 is None:
        raise HTTPException(status_code=500, detail="inconsistent state")
    return LlmEvaluateOut(verdict=verdict, pull_request=_pr_out(pr2))


@router.post("/prs/{pr_id}/votes", response_model=PullRequestOut)
def vote_pr(
    pr_id: str,
    body: VoteIn,
    session: Annotated[Session, Depends(get_db)],
) -> PullRequestOut:
    try:
        pr = record_vote(session, pr_id, body.validator_id, body.approved)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _pr_out(pr)


@router.post("/prs/{pr_id}/merge", response_model=PullRequestOut)
def merge_pr(
    pr_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> PullRequestOut:
    try:
        pr = merge_if_quorum(session, pr_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _pr_out(pr)


@router.post("/prs/{pr_id}/reject", response_model=PullRequestOut)
def reject_pull_request(
    pr_id: str,
    session: Annotated[Session, Depends(get_db)],
    reason: str = Query("", description="Optional rejection note."),
) -> PullRequestOut:
    try:
        pr = reject_pr(session, pr_id, reason=reason)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _pr_out(pr)


@router.post("/agents/{agent_id}/head", response_model=AgentOut)
def post_agent_head(
    agent_id: str,
    session: Annotated[Session, Depends(get_db)],
    head_sha: str = Query(..., description="Current HEAD commit for this agent."),
    swarm_id: str = "default",
    branch: str | None = Query(None, description="Optional branch name."),
) -> AgentOut:
    ensure_swarm_svc(session, swarm_id)
    a = upsert_agent(
        session,
        agent_id=agent_id,
        swarm_id=swarm_id,
        last_head_sha=head_sha,
        branch=branch,
    )
    return AgentOut(
        id=a.id,
        swarm_id=a.swarm_id,
        display_name=a.display_name,
        last_head_sha=a.last_head_sha,
        branch=a.branch,
        updated_at=a.updated_at,
    )


@router.get("/status", response_model=StatusResponse)
def get_status(
    session: Annotated[Session, Depends(get_db)],
    swarm_id: str = "default",
) -> StatusResponse:
    swarm = session.get(Swarm, swarm_id)
    if swarm is None:
        swarm = ensure_swarm_svc(session, swarm_id)
    stmt = select(Agent).where(Agent.swarm_id == swarm_id)
    agents = list(session.scalars(stmt))
    pr_stmt = (
        select(PullRequest)
        .where(PullRequest.swarm_id == swarm_id)
        .where(PullRequest.status == "open")
    )
    open_prs = list(session.scalars(pr_stmt))
    return StatusResponse(
        swarm=SwarmOut(
            id=swarm.id,
            name=swarm.name,
            quorum_threshold=swarm.quorum_threshold,
            validator_agent_ids=list(swarm.validator_agent_ids or []),
        ),
        agents=[
            AgentOut(
                id=a.id,
                swarm_id=a.swarm_id,
                display_name=a.display_name,
                last_head_sha=a.last_head_sha,
                branch=a.branch,
                updated_at=a.updated_at,
            )
            for a in agents
        ],
        open_pull_requests=[_pr_out(p) for p in open_prs],
    )


@router.post("/blackboard/append", response_model=BlackboardEntryOut)
def blackboard_append(
    body: BlackboardAppend,
    session: Annotated[Session, Depends(get_db)],
) -> BlackboardEntryOut:
    row = append_blackboard(
        session,
        swarm_id=body.swarm_id,
        agent_id=body.agent_id,
        payload=body.payload,
    )
    return BlackboardEntryOut(
        id=row.id,
        swarm_id=row.swarm_id,
        agent_id=row.agent_id,
        lamport=row.lamport,
        payload=row.payload,
        created_at=row.created_at,
    )


@router.get("/blackboard", response_model=list[BlackboardEntryOut])
def blackboard_list(
    session: Annotated[Session, Depends(get_db)],
    swarm_id: str = "default",
) -> list[BlackboardEntryOut]:
    rows = list_blackboard(session, swarm_id)
    return [
        BlackboardEntryOut(
            id=r.id,
            swarm_id=r.swarm_id,
            agent_id=r.agent_id,
            lamport=r.lamport,
            payload=r.payload,
            created_at=r.created_at,
        )
        for r in rows
    ]
