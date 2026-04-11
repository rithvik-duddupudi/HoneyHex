from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from honeyhex.ledger.git_store import HoneyHexLedger


class SwarmRemotes(BaseModel):
    """`.honeyhex/swarm.json` — named peers (local paths or Git remote URLs)."""

    model_config = {"extra": "forbid"}

    remotes: dict[str, str] = Field(default_factory=dict)


SWARM_FILE = "swarm.json"


def _ledger_path(cell_root: Path) -> Path:
    return HoneyHexLedger(cell_root).honeyhex_path


def swarm_path(cell_root: Path) -> Path:
    return _ledger_path(cell_root) / SWARM_FILE


def load_swarm_remotes(cell_root: Path) -> SwarmRemotes:
    path = swarm_path(cell_root)
    if not path.is_file():
        return SwarmRemotes()
    data = json.loads(path.read_text(encoding="utf-8"))
    return SwarmRemotes.model_validate(data)


def save_swarm_remotes(cell_root: Path, swarm: SwarmRemotes) -> None:
    path = swarm_path(cell_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(swarm.model_dump_json(indent=2), encoding="utf-8")


def _is_remote_url(raw: str) -> bool:
    s = raw.strip()
    return s.startswith(("http://", "https://", "git@", "ssh://"))


def _remote_git_url(cell_root: Path, name: str) -> str:
    swarm = load_swarm_remotes(cell_root)
    if name not in swarm.remotes:
        msg = f"remote {name!r} not configured in .honeyhex/{SWARM_FILE}"
        raise KeyError(msg)
    raw = swarm.remotes[name].strip()
    if _is_remote_url(raw):
        return raw
    peer_root = Path(raw).expanduser().resolve()
    honeyhex = peer_root / ".honeyhex"
    if not (honeyhex / ".git").is_dir():
        msg = f"remote path is not a HoneyHex cell: {raw}"
        raise ValueError(msg)
    return honeyhex.as_uri()


def _git_remote_name(name: str) -> str:
    return f"swarm-{name}"


def fetch_remote(cell_root: Path, name: str) -> dict[str, Any]:
    """Configure Git remote for `name` and run `git fetch`."""
    uri = _remote_git_url(cell_root, name)
    ledger = HoneyHexLedger(cell_root)
    repo = ledger.repo()
    git_name = _git_remote_name(name)
    if git_name in [r.name for r in repo.remotes]:
        repo.remotes[git_name].set_url(uri)
    else:
        repo.create_remote(git_name, uri)
    fetch_info = repo.remote(git_name).fetch()
    return {
        "remote": name,
        "git_remote": git_name,
        "url": uri,
        "fetched": len(fetch_info),
    }


def pull_remote(
    cell_root: Path,
    name: str,
    ref: str | None,
) -> dict[str, Any]:
    """Fetch, then merge remote branch into the current branch."""
    fetch_remote(cell_root, name)
    ledger = HoneyHexLedger(cell_root)
    repo = ledger.repo()
    git_name = _git_remote_name(name)
    branch = ref or repo.active_branch.name
    repo.git.pull(git_name, branch)
    return {
        "remote": name,
        "git_remote": git_name,
        "branch": branch,
        "head": repo.head.commit.hexsha,
    }


def add_remote(cell_root: Path, name: str, target: str | Path) -> None:
    swarm = load_swarm_remotes(cell_root)
    if name in swarm.remotes:
        msg = f"remote {name!r} already exists"
        raise ValueError(msg)
    s = str(target).strip()
    if _is_remote_url(s):
        swarm.remotes[name] = s
        save_swarm_remotes(cell_root, swarm)
        return
    resolved = Path(s).expanduser().resolve()
    if not (resolved / ".honeyhex").is_dir():
        msg = "path must contain a .honeyhex directory (or use an https/git URL)"
        raise ValueError(msg)
    swarm.remotes[name] = str(resolved)
    save_swarm_remotes(cell_root, swarm)


def remove_remote(cell_root: Path, name: str) -> None:
    swarm = load_swarm_remotes(cell_root)
    if name not in swarm.remotes:
        msg = f"remote {name!r} not found"
        raise KeyError(msg)
    del swarm.remotes[name]
    save_swarm_remotes(cell_root, swarm)
