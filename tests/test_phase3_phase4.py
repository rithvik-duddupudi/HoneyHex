from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from honeyhex.branching.git_ops import (
    checkout_new_branch,
    cherry_pick,
    rebase_interactive_drop,
)
from honeyhex.branching.shadow import run_dual_shell_commands
from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff
from honeyhex.daemon.config import DaemonConfig
from honeyhex.daemon.service import HiveDaemon
from honeyhex.ledger.git_store import HoneyHexLedger
from honeyhex.mesh.publish import announce_head, read_head_sha


def _three_file_commits(cell: Path) -> tuple[str, str, str]:
    ledger = HoneyHexLedger(cell)
    repo = ledger.init_if_missing()
    base = ledger.honeyhex_path
    track = base / "track"
    track.mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(["f1.txt", "f2.txt", "f3.txt"], start=1):
        (track / name).write_text(str(i), encoding="utf-8")
        repo.index.add([f"track/{name}"])
        repo.index.commit(f"c{i}")
    commits = list(repo.iter_commits(max_count=3))
    return commits[2].hexsha, commits[1].hexsha, commits[0].hexsha


def test_checkout_new_branch_and_cherry_pick(tmp_path: Path) -> None:
    c1, c2, _c3 = _three_file_commits(tmp_path)
    ledger = HoneyHexLedger(tmp_path)
    repo = ledger.repo()
    default = repo.active_branch.name
    checkout_new_branch(tmp_path, "hypothesis")
    assert repo.active_branch.name == "hypothesis"
    repo.git.reset("--hard", c1)
    new_head = cherry_pick(tmp_path, c2)
    assert len(new_head) == 40
    assert (ledger.honeyhex_path / "track" / "f2.txt").read_text() == "2"
    repo.git.checkout(default)


def test_shadow_first_success_wins() -> None:
    r = asyncio.run(run_dual_shell_commands("true", "sleep 8"))
    assert r.winner in ("left", "right")
    assert r.returncode == 0


def test_shadow_both_fail() -> None:
    with pytest.raises(RuntimeError, match="without success"):
        asyncio.run(run_dual_shell_commands("false", "false"))


def test_rebase_interactive_drop_middle(tmp_path: Path) -> None:
    c1, c2, c3 = _three_file_commits(tmp_path)
    ledger = HoneyHexLedger(tmp_path)
    repo = ledger.repo()
    assert repo.head.commit.hexsha == c3
    new_head = rebase_interactive_drop(tmp_path, c1, [c2])
    assert new_head != c3
    assert (ledger.honeyhex_path / "track" / "f1.txt").read_text() == "1"
    assert (ledger.honeyhex_path / "track" / "f3.txt").read_text() == "3"
    assert not (ledger.honeyhex_path / "track" / "f2.txt").exists()


def test_read_head_after_commit(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    t = mgr.commit("m", StateDiff(prompt="x"))
    assert read_head_sha(tmp_path) == t.commit_hash


def test_hive_daemon_apply_event() -> None:
    d = HiveDaemon(DaemonConfig("redis://127.0.0.1:6379/15"))
    d.apply_event({"type": "head_update", "agent": "a1", "head": "abc"})
    assert d.heads["a1"] == "abc"
    truths: list[str] = []

    def on_truth(s: str) -> None:
        truths.append(s)

    d2 = HiveDaemon(DaemonConfig("redis://127.0.0.1:6379/15"), on_truth_commit=on_truth)
    d2.apply_event({"type": "truth_commit", "commit": "deadbeef"})
    assert d2.truth_commits == ["deadbeef"]
    assert truths == ["deadbeef"]
    d.stop()
    d2.stop()


def test_daemon_pr_created_event() -> None:
    d = HiveDaemon(DaemonConfig("redis://127.0.0.1:6379/15"))
    d.apply_event(
        {
            "type": "pr_created",
            "pr_id": "p1",
            "source": "a",
            "target": "b",
            "head": "c0ffee",
        },
    )
    assert len(d.pr_events) == 1
    d.stop()


def test_announce_head_publishes() -> None:
    mock_redis = MagicMock()
    with patch(
        "honeyhex.mesh.publish._redis_client_class",
        return_value=mock_redis,
    ):
        announce_head("redis://localhost:6379/0", "ch", "agent-1", "sha1")
        mock_redis.from_url.assert_called_once()
        inst = mock_redis.from_url.return_value
        inst.publish.assert_called_once()
        inst.close.assert_called_once()
