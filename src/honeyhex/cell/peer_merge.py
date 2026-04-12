from __future__ import annotations

from pathlib import Path
from typing import Literal

from git.exc import GitCommandError

from honeyhex.cell.remotes import fetch_remote
from honeyhex.ledger.git_store import HoneyHexLedger

MergeFavor = Literal["none", "ours", "theirs"]


def _git_remote_name(name: str) -> str:
    return f"swarm-{name}"


def merge_peer_ledger(
    cell_root: Path,
    remote_name: str,
    *,
    branch: str | None = None,
    favor: MergeFavor = "none",
) -> str:
    """
    Fetch a configured swarm remote and merge its branch into the current branch
    (same semantics as `git merge swarm-<name>/<branch>`).
    """
    fetch_remote(cell_root, remote_name)
    ledger = HoneyHexLedger(cell_root)
    repo = ledger.repo()
    git_name = _git_remote_name(remote_name)
    br = branch or repo.active_branch.name
    ref = f"{git_name}/{br}"
    try:
        if favor == "none":
            repo.git.merge(ref, allow_unrelated_histories=True)
        elif favor == "ours":
            repo.git.merge(ref, allow_unrelated_histories=True, X="ours")
        else:
            repo.git.merge(ref, allow_unrelated_histories=True, X="theirs")
    except GitCommandError as e:
        msg = f"merge {ref!r} failed: {e}"
        raise ValueError(msg) from e
    return repo.head.commit.hexsha
