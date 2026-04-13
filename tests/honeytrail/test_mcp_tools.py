# tests/honeytrail/test_mcp_tools.py
"""Integration tests for MCP tool handlers using an in-memory TrailStore."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from honeytrail.db.store import TrailStore
from honeytrail.server import call_tool


def _make_store(tmp_path: Path) -> TrailStore:
    return TrailStore(tmp_path / "test.db")


@pytest.mark.anyio
async def test_trail_session_open(tmp_path: Path) -> None:
    with patch("honeytrail.server._db", return_value=_make_store(tmp_path)):
        result = await call_tool("trail_session_open", {"label": "test-session"})
    assert len(result) == 1
    sid = result[0].text
    assert len(sid) == 32  # uuid4().hex


@pytest.mark.anyio
async def test_trail_append_thought(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    sid = store.session_open("append-test")
    store.close()

    with patch("honeytrail.server._db", return_value=_make_store(tmp_path)):
        result = await call_tool(
            "trail_append_thought",
            {"session_id": sid, "monologue": "thinking about X", "summary": "X"},
        )
    assert len(result) == 1
    node_id = result[0].text
    assert len(node_id) == 32


@pytest.mark.anyio
async def test_trail_append_tool(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    sid = store.session_open("tool-test")
    store.close()

    with patch("honeytrail.server._db", return_value=_make_store(tmp_path)):
        result = await call_tool(
            "trail_append_tool",
            {
                "session_id": sid,
                "tool_name": "read_file",
                "tool_input_json": json.dumps({"path": "/foo.py"}),
                "tool_output_summary": "file contents",
            },
        )
    assert len(result) == 1
    node_id = result[0].text
    assert len(node_id) == 32


@pytest.mark.anyio
async def test_trail_get_branch(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    sid = store.session_open("branch-test")
    store.append_thought(sid, "step one", "s1")
    store.append_thought(sid, "step two", "s2")
    store.close()

    with patch("honeytrail.server._db", return_value=_make_store(tmp_path)):
        result = await call_tool("trail_get_branch", {"session_id": sid})
    assert len(result) == 1
    lines = result[0].text.strip().split("\n")
    assert len(lines) == 2
    assert "s1" in lines[0]
    assert "s2" in lines[1]


@pytest.mark.anyio
async def test_trail_rollback(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    sid = store.session_open("rollback-test")
    store.append_thought(sid, "safe step", "safe")
    store.append_thought(sid, "dangerous schema change", "bad")
    store.append_thought(sid, "after bad", "after")
    store.close()

    with patch("honeytrail.server._db", return_value=_make_store(tmp_path)):
        result = await call_tool(
            "trail_rollback",
            {"session_id": sid, "before_substring": "schema change"},
        )
    assert "rolled back" in result[0].text


@pytest.mark.anyio
async def test_trail_fork_and_merge(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    sid = store.session_open("fork-merge-test")
    root_id = store.append_thought(sid, "root thought", "root")
    store.close()

    with patch("honeytrail.server._db", return_value=_make_store(tmp_path)):
        fork_result = await call_tool(
            "trail_fork",
            {"session_id": sid, "branch_name": "alt", "from_node_id": root_id},
        )
    fork_id = fork_result[0].text
    assert len(fork_id) == 32

    # checkout alt branch then merge main back in
    store2 = _make_store(tmp_path)
    store2.checkout_branch(sid, "alt")
    store2.append_thought(sid, "alt idea", "alt")
    store2.close()

    with patch("honeytrail.server._db", return_value=_make_store(tmp_path)):
        merge_result = await call_tool(
            "trail_merge",
            {"session_id": sid, "other_branch": "main", "summary": "merged"},
        )
    merge_id = merge_result[0].text
    assert len(merge_id) == 32


@pytest.mark.anyio
async def test_unknown_tool(tmp_path: Path) -> None:
    with patch("honeytrail.server._db", return_value=_make_store(tmp_path)):
        result = await call_tool("nonexistent_tool", {})
    assert "unknown tool" in result[0].text
