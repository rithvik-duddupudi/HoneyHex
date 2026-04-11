from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from honeyhex.ledger.git_store import HoneyHexLedger
from honeyhex.mesh.publish import read_head_sha
from honeyhex.mesh.registry_pr import post_pr_to_registry


class PendingPR(BaseModel):
    """Queued PR intent for later `hex sync` / `hex outbox sync`."""

    model_config = {"extra": "forbid"}

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    swarm_id: str = "default"
    source_agent_id: str
    target_agent_id: str
    head_sha: str
    title: str
    enqueued_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )


def _dirs(cell_root: Path) -> tuple[Path, Path]:
    base = HoneyHexLedger(cell_root).honeyhex_path / "outbox"
    pending = base / "pending"
    failed = base / "failed"
    pending.mkdir(parents=True, exist_ok=True)
    failed.mkdir(parents=True, exist_ok=True)
    return pending, failed


def enqueue_pr(
    cell_root: Path,
    *,
    source: str,
    target: str,
    swarm_id: str,
    title: str,
    head_sha: str | None = None,
) -> PendingPR:
    root = cell_root.resolve()
    head = head_sha if head_sha is not None else read_head_sha(root)
    item = PendingPR(
        swarm_id=swarm_id,
        source_agent_id=source,
        target_agent_id=target,
        head_sha=head,
        title=title or f"{source} -> {target}",
    )
    pending, _ = _dirs(root)
    path = pending / f"{item.id}.json"
    path.write_text(item.model_dump_json(indent=2), encoding="utf-8")
    return item


def list_pending(cell_root: Path) -> list[PendingPR]:
    pending, _ = _dirs(cell_root.resolve())
    out: list[PendingPR] = []
    for p in sorted(pending.glob("*.json")):
        out.append(PendingPR.model_validate_json(p.read_text(encoding="utf-8")))
    return out


def sync_outbox(
    cell_root: Path,
    *,
    refresh_head: bool = False,
) -> dict[str, Any]:
    """
    POST each pending item to the registry; remove file on success.
    On failure, move JSON to `outbox/failed/`.
    """
    root = cell_root.resolve()
    pending, failed = _dirs(root)
    results: list[dict[str, Any]] = []
    for path in sorted(pending.glob("*.json")):
        item = PendingPR.model_validate_json(path.read_text(encoding="utf-8"))
        head = read_head_sha(root) if refresh_head else item.head_sha
        try:
            resp = post_pr_to_registry(
                root,
                source=item.source_agent_id,
                target=item.target_agent_id,
                swarm_id=item.swarm_id,
                title=item.title,
                head_sha=head,
            )
            path.unlink()
            results.append({"id": item.id, "ok": True, "response": resp})
        except Exception as e:
            dest = failed / path.name
            dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            path.unlink()
            results.append({"id": item.id, "ok": False, "error": str(e)})
    return {"synced": len([r for r in results if r.get("ok")]), "results": results}
