from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from honeyhex.ledger.git_store import HoneyHexLedger


def _redis_client_class() -> Any:
    try:
        from redis import Redis
    except ImportError as e:
        msg = "Install the redis extra: pip install 'honeyhex[redis]'"
        raise ImportError(msg) from e
    return Redis


def read_head_sha(cell_root: Path) -> str:
    """Return current `.honeyhex` HEAD commit hexsha."""
    ledger = HoneyHexLedger(cell_root)
    repo = ledger.repo()
    return repo.head.commit.hexsha


def head_event_json(agent_id: str, head_sha: str) -> str:
    return json.dumps(
        {"type": "head_update", "agent": agent_id, "head": head_sha},
        separators=(",", ":"),
    )


def truth_commit_json(commit_sha: str) -> str:
    payload = {"type": "truth_commit", "commit": commit_sha}
    return json.dumps(payload, separators=(",", ":"))


def pr_created_json(
    pr_id: str,
    source_agent: str,
    target_agent: str,
    head_sha: str,
) -> str:
    return json.dumps(
        {
            "type": "pr_created",
            "pr_id": pr_id,
            "source": source_agent,
            "target": target_agent,
            "head": head_sha,
        },
        separators=(",", ":"),
    )


def announce_pr_created(
    redis_url: str,
    channel: str,
    *,
    pr_id: str,
    source_agent: str,
    target_agent: str,
    head_sha: str,
) -> None:
    Redis = _redis_client_class()
    client: Any = Redis.from_url(redis_url, decode_responses=True)
    try:
        client.publish(
            channel,
            pr_created_json(pr_id, source_agent, target_agent, head_sha),
        )
    finally:
        client.close()


def announce_truth_commit(redis_url: str, channel: str, commit_sha: str) -> None:
    """Publish a global truth commit (triggers Hive-Daemon / agents to rebase)."""
    Redis = _redis_client_class()
    client: Any = Redis.from_url(redis_url, decode_responses=True)
    try:
        client.publish(channel, truth_commit_json(commit_sha))
    finally:
        client.close()


def announce_head(redis_url: str, channel: str, agent_id: str, head_sha: str) -> None:
    """Publish a HEAD update to the mesh channel (requires `redis` extra)."""
    Redis = _redis_client_class()
    client: Any = Redis.from_url(redis_url, decode_responses=True)
    try:
        client.publish(channel, head_event_json(agent_id, head_sha))
    finally:
        client.close()
