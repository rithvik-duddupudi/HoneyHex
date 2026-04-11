from __future__ import annotations

import sys
from pathlib import Path

from git import Repo
from git.objects.commit import Commit

from honeyhex.cell.hooks import HookContext, run_named_hook
from honeyhex.commit.models import StateDiff, ThoughtCommit, payload_relative_path
from honeyhex.ledger.git_store import HoneyHexLedger


def _head_commit(repo: Repo) -> Commit | None:
    try:
        return repo.head.commit
    except ValueError:
        return None


class CommitManager:
    """Records thought-commits as append-only Git history under `.honeyhex/`."""

    def __init__(self, cell_root: Path) -> None:
        self._ledger = HoneyHexLedger(cell_root)
        self._payload_rel = payload_relative_path()

    def ensure_ledger(self) -> Repo:
        return self._ledger.init_if_missing()

    def commit(self, internal_monologue: str, diff: StateDiff) -> ThoughtCommit:
        """Write snapshot JSON (no self-hash) and one Git commit per thought."""
        repo = self.ensure_ledger()
        pre = run_named_hook(HookContext(self._ledger.cell_root, "pre-thought"))
        if pre.returncode != 0:
            if pre.stdout:
                sys.stdout.write(pre.stdout)
            if pre.stderr:
                sys.stderr.write(pre.stderr)
            msg = f"pre-thought hook failed with exit code {pre.returncode}"
            raise RuntimeError(msg)
        honeyhex_root = self._ledger.honeyhex_path
        thoughts_dir = honeyhex_root / "thoughts"
        thoughts_dir.mkdir(parents=True, exist_ok=True)
        payload_path = honeyhex_root / self._payload_rel

        parent = _head_commit(repo)
        parent_hash = parent.hexsha if parent else None

        provisional = ThoughtCommit(
            commit_hash="",
            parent_hash=parent_hash,
            internal_monologue=internal_monologue,
            diff=diff,
        )
        payload_path.write_text(
            provisional.model_dump_json(indent=2, exclude={"commit_hash"}),
            encoding="utf-8",
        )
        repo.index.add([self._payload_rel])
        repo.index.commit(internal_monologue)

        head = _head_commit(repo)
        if head is None:
            msg = "expected HEAD after index.commit"
            raise RuntimeError(msg)
        thought = provisional.model_copy(update={"commit_hash": head.hexsha})
        post = run_named_hook(HookContext(self._ledger.cell_root, "post-thought"))
        if post.returncode != 0:
            if post.stdout:
                sys.stdout.write(post.stdout)
            if post.stderr:
                sys.stderr.write(post.stderr)
        return thought
