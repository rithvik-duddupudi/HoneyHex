from __future__ import annotations

from pathlib import Path

from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff


def test_commit_creates_honeyhex_and_chain(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    a = mgr.commit("think one", StateDiff(prompt="p1", scratchpad="s1"))
    assert a.parent_hash is None
    assert len(a.commit_hash) == 40

    b = mgr.commit("think two", StateDiff(prompt="p2", rag_context="r2"))
    assert b.parent_hash == a.commit_hash

    honeyhex = tmp_path / ".honeyhex"
    assert (honeyhex / ".git").is_dir()
    snap = honeyhex / "thoughts" / "snapshot.json"
    assert snap.is_file()
    assert "p2" in snap.read_text()


def test_state_diff_tool_outputs_roundtrip(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    d = StateDiff(prompt="x", tool_outputs=[{"tool": "t", "out": 1}])
    t = mgr.commit("m", d)
    assert t.diff.prompt == "x"
    assert t.diff.tool_outputs == [{"tool": "t", "out": 1}]
