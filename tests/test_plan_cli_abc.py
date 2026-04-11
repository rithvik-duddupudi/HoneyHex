from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from honeyhex.branching.git_ops import checkout_new_branch, merge_branch
from honeyhex.cell.remotes import add_remote, fetch_remote, pull_remote
from honeyhex.cell.scaffold import init_cell
from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff
from honeyhex.inspect.core import (
    diff_snapshots,
    git_blame_snapshot,
    git_reflog,
    iter_log,
    read_snapshot_at,
    show_revision,
)
from honeyhex.ledger.git_store import HoneyHexLedger


def test_inspect_log_show_diff_three_commits(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    mgr.commit("a", StateDiff(prompt="p1"))
    mgr.commit("b", StateDiff(prompt="p2"))
    mgr.commit("c", StateDiff(prompt="p3"))

    entries = iter_log(tmp_path, max_count=10)
    assert len(entries) == 3
    assert "c" in entries[0].message

    text = show_revision(tmp_path, "HEAD", as_json=False)
    assert "p3" in text
    _, snap = read_snapshot_at(tmp_path, "HEAD")
    assert snap is not None
    assert snap.prompt == "p3"

    diff_txt = diff_snapshots(tmp_path, None, None)
    assert "p2" in diff_txt or "p3" in diff_txt


def test_fetch_remote_local_peer(tmp_path: Path) -> None:
    peer = tmp_path / "peer"
    local = tmp_path / "local"
    peer.mkdir()
    local.mkdir()
    mp = CommitManager(peer)
    mp.commit("peer-1", StateDiff(prompt="from-peer"))
    ml = CommitManager(local)
    ml.commit("local-1", StateDiff(prompt="local-only"))

    add_remote(local, "origin", peer)
    info = fetch_remote(local, "origin")
    assert info["remote"] == "origin"
    assert info["fetched"] >= 1


def test_pull_remote_fast_forward(tmp_path: Path) -> None:
    peer_root = tmp_path / "peer"
    peer_root.mkdir()
    mp = CommitManager(peer_root)
    mp.commit("p1", StateDiff(prompt="x"))
    mp.commit("p2", StateDiff(prompt="y"))

    local_root = tmp_path / "local"
    local_root.mkdir()
    subprocess.run(
        [
            "git",
            "clone",
            str(peer_root / ".honeyhex"),
            str(local_root / ".honeyhex"),
        ],
        check=True,
        capture_output=True,
    )

    mp.commit("p3", StateDiff(prompt="z"))
    add_remote(local_root, "up", peer_root)
    out = pull_remote(local_root, "up", None)
    assert len(out["head"]) == 40
    snap = (local_root / ".honeyhex" / "thoughts" / "snapshot.json").read_text()
    assert "z" in snap


def test_pre_thought_aborts_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HONEYHEX_HOOKS", "full")
    init_cell(tmp_path, hook_stubs=True)
    pre = tmp_path / ".honeyhex" / "hooks" / "pre-thought.sh"
    pre.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    pre.chmod(0o755)

    mgr = CommitManager(tmp_path)
    with pytest.raises(RuntimeError, match="pre-thought hook failed"):
        mgr.commit("should-not-record", StateDiff(prompt="n"))


def test_cell_init_creates_config(tmp_path: Path) -> None:
    out = init_cell(tmp_path, hook_stubs=False)
    assert "honeyhex" in out
    assert (Path(out["honeyhex"]) / "config.json").is_file()


def test_blame_reflog_tag_smoke(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    mgr.commit("t1", StateDiff(prompt="trace"))
    b = git_blame_snapshot(tmp_path, None)
    assert "snapshot.json" in b or "trace" in b
    r = git_reflog(tmp_path, 5)
    assert "HEAD@" in r or r.strip() != ""
    from honeyhex.branching.git_ops import create_lightweight_tag

    create_lightweight_tag(tmp_path, "v-test")
    ledger = HoneyHexLedger(tmp_path)
    tags = [t.name for t in ledger.repo().tags]
    assert "v-test" in tags


def test_merge_second_branch(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    mgr.commit("base", StateDiff(prompt="1"))
    ledger = HoneyHexLedger(tmp_path)
    main_name = ledger.repo().active_branch.name
    checkout_new_branch(tmp_path, "feature")
    mgr.commit("on-feature", StateDiff(prompt="2"))
    ledger.repo().git.checkout(main_name)
    merge_branch(tmp_path, "feature")
    assert "2" in (ledger.honeyhex_path / "thoughts" / "snapshot.json").read_text()
