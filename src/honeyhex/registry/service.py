from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from honeyhex.registry.models import Agent, BlackboardEntry, PullRequest, Swarm


def ensure_swarm(session: Session, swarm_id: str) -> Swarm:
    row = session.get(Swarm, swarm_id)
    if row is None:
        row = Swarm(
            id=swarm_id,
            name=swarm_id,
            quorum_threshold=0.51,
            validator_agent_ids=["validator-a", "validator-b", "validator-c"],
        )
        session.add(row)
        session.flush()
    return row


def upsert_agent(
    session: Session,
    *,
    agent_id: str,
    swarm_id: str,
    last_head_sha: str | None = None,
    branch: str | None = None,
) -> Agent:
    ensure_swarm(session, swarm_id)
    row = session.get(Agent, agent_id)
    if row is None:
        row = Agent(
            id=agent_id,
            swarm_id=swarm_id,
            last_head_sha=last_head_sha,
            branch=branch,
        )
        session.add(row)
    else:
        if last_head_sha is not None:
            row.last_head_sha = last_head_sha
        if branch is not None:
            row.branch = branch
        row.updated_at = datetime.now(UTC)
    session.flush()
    return row


def create_pull_request(
    session: Session,
    *,
    swarm_id: str,
    source_agent_id: str,
    target_agent_id: str,
    head_sha: str,
    title: str,
) -> PullRequest:
    swarm = ensure_swarm(session, swarm_id)
    upsert_agent(session, agent_id=source_agent_id, swarm_id=swarm.id)
    upsert_agent(session, agent_id=target_agent_id, swarm_id=swarm.id)
    pr = PullRequest(
        swarm_id=swarm.id,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        head_sha=head_sha,
        title=title or f"PR {source_agent_id} -> {target_agent_id}",
        status="open",
        votes={},
    )
    session.add(pr)
    session.flush()
    return pr


def cast_votes_to_bool(votes: dict[str, Any]) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for k, v in votes.items():
        out[str(k)] = bool(v)
    return out


def record_vote(
    session: Session,
    pr_id: str,
    validator_id: str,
    approved: bool,
) -> PullRequest:
    pr = session.get(PullRequest, pr_id)
    if pr is None:
        msg = "pull request not found"
        raise KeyError(msg)
    if pr.status != "open":
        msg = "pull request is not open"
        raise ValueError(msg)
    swarm = session.get(Swarm, pr.swarm_id)
    if swarm is None:
        msg = "swarm missing"
        raise RuntimeError(msg)
    if validator_id not in swarm.validator_agent_ids:
        msg = "validator not registered for this swarm"
        raise ValueError(msg)
    votes = dict(pr.votes or {})
    votes[validator_id] = approved
    pr.votes = votes
    session.flush()
    return pr


def quorum_fraction(swarm: Swarm, votes: dict[str, Any]) -> float:
    vals = cast_votes_to_bool(votes)
    validators = list(swarm.validator_agent_ids)
    if not validators:
        return 0.0
    approvals = sum(1 for vid in validators if vals.get(vid) is True)
    return approvals / len(validators)


def merge_if_quorum(session: Session, pr_id: str) -> PullRequest:
    pr = session.get(PullRequest, pr_id)
    if pr is None:
        msg = "pull request not found"
        raise KeyError(msg)
    swarm = session.get(Swarm, pr.swarm_id)
    if swarm is None:
        msg = "swarm missing"
        raise RuntimeError(msg)
    frac = quorum_fraction(swarm, pr.votes or {})
    if frac < swarm.quorum_threshold:
        msg = "quorum not met"
        raise ValueError(msg)
    pr.status = "merged"
    session.flush()
    return pr


def reject_pr(session: Session, pr_id: str, *, reason: str = "") -> PullRequest:
    pr = session.get(PullRequest, pr_id)
    if pr is None:
        msg = "pull request not found"
        raise KeyError(msg)
    pr.status = "rejected"
    if reason:
        pr.title = f"{pr.title} [{reason}]"[:512]
    session.flush()
    return pr


def next_lamport(session: Session, swarm_id: str) -> int:
    stmt = select(func.coalesce(func.max(BlackboardEntry.lamport), 0)).where(
        BlackboardEntry.swarm_id == swarm_id,
    )
    m = session.scalar(stmt)
    return int(m or 0) + 1


def append_blackboard(
    session: Session,
    *,
    swarm_id: str,
    agent_id: str,
    payload: dict[str, Any],
) -> BlackboardEntry:
    ensure_swarm(session, swarm_id)
    lam = next_lamport(session, swarm_id)
    row = BlackboardEntry(
        swarm_id=swarm_id,
        agent_id=agent_id,
        lamport=lam,
        payload=payload,
    )
    session.add(row)
    session.flush()
    return row


def list_blackboard(session: Session, swarm_id: str) -> list[BlackboardEntry]:
    stmt = (
        select(BlackboardEntry)
        .where(BlackboardEntry.swarm_id == swarm_id)
        .order_by(BlackboardEntry.lamport.asc(), BlackboardEntry.id.asc())
    )
    return list(session.scalars(stmt))
