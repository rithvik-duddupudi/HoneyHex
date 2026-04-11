from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff
from honeyhex.inspect.core import read_snapshot_at
from honeyhex.ledger.git_store import HoneyHexLedger


def create_bundle(
    cell_root: Path,
    zip_path: Path,
    *,
    max_count: int | None = None,
) -> dict[str, Any]:
    """
    Write a ZIP with `manifest.json` and thought history (oldest .. newest).
    """
    root = cell_root.resolve()
    ledger = HoneyHexLedger(root)
    repo = ledger.repo()
    commits = list(repo.iter_commits(max_count=max_count))
    commits.reverse()
    entries: list[dict[str, Any]] = []
    for c in commits:
        sha = c.hexsha
        _, snap = read_snapshot_at(root, sha)
        if snap is None:
            continue
        entries.append(
            {
                "sha": sha,
                "message": str(c.message).strip() if c.message else "",
                "snapshot": snap.model_dump(),
            },
        )
    manifest = {"version": 1, "format": "honeyhex-bundle", "commit_count": len(entries)}
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("thoughts.json", json.dumps(entries, indent=2))
    return {"path": str(zip_path), **manifest}


def replay_bundle(cell_root: Path, zip_path: Path) -> dict[str, Any]:
    """Replay bundled thoughts as new commits (linear history)."""
    root = cell_root.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        raw = zf.read("thoughts.json")
    entries: list[dict[str, Any]] = json.loads(raw.decode("utf-8"))
    mgr = CommitManager(root)
    applied = 0
    for e in entries:
        msg = str(e.get("message", "replay"))
        snap = StateDiff.model_validate(e["snapshot"])
        mgr.commit(msg, snap)
        applied += 1
    return {"replayed": applied, "cell": str(root)}
