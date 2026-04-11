from __future__ import annotations

from pathlib import Path

from git import Repo
from git.exc import GitCommandError

from honeyhex.ledger.git_store import HoneyHexLedger


def _repo(cell_root: Path) -> Repo:
    ledger = HoneyHexLedger(cell_root)
    return ledger.repo()


def _normalize_sha(repo: Repo, sha: str) -> str:
    commit = repo.commit(sha)
    return commit.hexsha


def checkout_new_branch(cell_root: Path, branch: str) -> None:
    """Create and switch to a new branch in `.honeyhex` (like `git checkout -b`)."""
    repo = _repo(cell_root)
    repo.git.checkout("-b", branch)


def cherry_pick(cell_root: Path, commit_sha: str) -> str:
    """Cherry-pick a commit onto the current branch; returns new HEAD hexsha."""
    repo = _repo(cell_root)
    full = _normalize_sha(repo, commit_sha)
    repo.git.cherry_pick(full)
    return repo.head.commit.hexsha


def rebase_interactive_drop(
    cell_root: Path,
    onto_sha: str,
    drop_shas: list[str],
    *,
    fix_message: str | None = None,
    fix_prompt_rel: str = "thoughts/fix_prompt.txt",
) -> str:
    """
    Reset to `onto`, then cherry-pick commits from the old (onto..HEAD] chain
    excluding any commit whose hash is in `drop_shas`.
    Optionally writes `thoughts/fix_prompt.txt` and commits it with `fix_message`.
    """
    repo = _repo(cell_root)
    honeyhex_root = HoneyHexLedger(cell_root).honeyhex_path
    onto_full = _normalize_sha(repo, onto_sha)
    drop_full = {_normalize_sha(repo, s) for s in drop_shas}

    head = repo.head.commit
    try:
        commits = list(repo.iter_commits(f"{onto_full}..{head.hexsha}", reverse=True))
    except GitCommandError as e:
        msg = "invalid onto or range; onto must be an ancestor of HEAD"
        raise ValueError(msg) from e

    kept = [c for c in commits if c.hexsha not in drop_full]
    unknown = drop_full - {c.hexsha for c in commits}
    if unknown:
        msg = f"drop commits not in (onto..HEAD]: {unknown!r}"
        raise ValueError(msg)

    repo.git.reset("--hard", onto_full)
    for c in kept:
        repo.git.cherry_pick(c.hexsha)

    head_sha = repo.head.commit.hexsha

    if fix_message is not None:
        rel = fix_prompt_rel
        path = honeyhex_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(fix_message, encoding="utf-8")
        repo.index.add([rel])
        repo.index.commit("rebase: fix prompt")

    return head_sha


def merge_branch(cell_root: Path, branch: str) -> str:
    """Merge `branch` into the current `.honeyhex` branch."""
    repo = _repo(cell_root)
    repo.git.merge(branch)
    return repo.head.commit.hexsha


def create_lightweight_tag(cell_root: Path, name: str) -> str:
    """Create a tag at HEAD in `.honeyhex`."""
    repo = _repo(cell_root)
    repo.git.tag(name, "HEAD")
    return name
