from __future__ import annotations

import re
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

from honeyhex.branching.git_ops import checkout_new_branch, merge_branch
from honeyhex.cell.config import CellConfig, load_cell_config
from honeyhex.ledger.git_store import HoneyHexLedger

EXP_PREFIX = "honeyhex/exp/"

_slug_re = re.compile(r"[^a-z0-9._-]+", re.I)


def sanitize_experiment_slug(raw: str) -> str:
    s = raw.strip().lower().replace(" ", "-")
    s = _slug_re.sub("-", s).strip("-")
    if not s:
        msg = "experiment slug must contain letters, digits, or hyphens"
        raise ValueError(msg)
    return s[:120]


def experiment_branch_name(slug: str) -> str:
    return f"{EXP_PREFIX}{sanitize_experiment_slug(slug)}"


def _repo(cell_root: Path) -> Repo:
    return HoneyHexLedger(cell_root).repo()


def list_experiment_branches(cell_root: Path) -> list[str]:
    repo = _repo(cell_root)
    out: list[str] = []
    for h in repo.heads:
        if h.name.startswith(EXP_PREFIX):
            out.append(h.name)
    return sorted(out)


def current_branch_name(cell_root: Path) -> str:
    repo = _repo(cell_root)
    if repo.head.is_detached:
        msg = "detached HEAD — checkout a branch first"
        raise ValueError(msg)
    return repo.active_branch.name


def experiment_start(cell_root: Path, slug: str) -> str:
    """Create and switch to honeyhex/exp/<slug>, or switch if it already exists."""
    branch = experiment_branch_name(slug)
    repo = _repo(cell_root)
    names = {h.name for h in repo.heads}
    if branch in names:
        repo.git.checkout(branch)
    else:
        checkout_new_branch(cell_root, branch)
    return branch


def experiment_status(cell_root: Path) -> dict[str, str | bool]:
    name = current_branch_name(cell_root)
    return {
        "branch": name,
        "experiment": str(name.startswith(EXP_PREFIX)),
    }


def _resolve_merge_target(cell_root: Path, cfg: CellConfig, into: str | None) -> str:
    if into is not None:
        return into
    repo = _repo(cell_root)
    names = {h.name for h in repo.heads}
    if cfg.default_branch in names:
        return cfg.default_branch
    if len(names) == 1:
        return next(iter(names))
    if "main" in names:
        return "main"
    if "master" in names:
        return "master"
    return cfg.default_branch


def experiment_merge(cell_root: Path, into: str | None = None) -> str:
    """Merge current experiment branch into default branch (or `into`)."""
    cfg = load_cell_config(cell_root)
    target = _resolve_merge_target(cell_root, cfg, into)
    cur = current_branch_name(cell_root)
    if not cur.startswith(EXP_PREFIX):
        msg = f"not on an experiment branch (expected prefix {EXP_PREFIX!r})"
        raise ValueError(msg)
    repo = _repo(cell_root)
    try:
        repo.git.checkout(target)
    except GitCommandError as e:
        msg = f"checkout {target!r} failed: {e}"
        raise ValueError(msg) from e
    try:
        head = merge_branch(cell_root, cur)
    except GitCommandError as e:
        repo.git.checkout(cur)
        msg = f"merge failed: {e}"
        raise ValueError(msg) from e
    return head
