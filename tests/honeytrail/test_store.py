from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from honeytrail.db.store import TrailStore


def test_session_and_two_thoughts(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    store = TrailStore(db)
    sid = store.session_open(label="test")
    n1 = store.append_thought(session_id=sid, monologue="consider A", summary="A")
    n2 = store.append_thought(session_id=sid, monologue="choose B", summary="B")
    head = store.get_head(sid)
    assert head == n2
    p = store.get_parent(n2)
    assert p == n1
    store.close()


def test_rollback_before_substring(tmp_path: Path) -> None:
    from honeytrail.db.store import TrailStore

    store = TrailStore(tmp_path / "t.db")
    sid = store.session_open("r")
    store.append_thought(sid, "ok", "n1")
    bad = store.append_thought(sid, "change database schema", "n2")
    store.append_thought(sid, "oops loop", "n3")
    rb = store.rollback_to_parent_of_match(sid, before_substring="schema")
    assert rb.previous_head_id is not None
    head = store.get_head(sid)
    assert head != bad
    assert store.get_node(head).monologue == "ok"
    store.close()


def test_branch_path(tmp_path: Path) -> None:
    from honeytrail.db.store import TrailStore

    s = TrailStore(tmp_path / "t.db")
    sid = s.session_open("p")
    a = s.append_thought(sid, "a", "a")
    b = s.append_thought(sid, "b", "b")
    path = s.linear_path_to_head(sid)
    assert [n.id for n in path] == [a, b]
    s.close()


def test_fork_and_merge(tmp_path: Path) -> None:
    from honeytrail.db.store import TrailStore

    st = TrailStore(tmp_path / "t.db")
    sid = st.session_open("m")
    st.append_thought(sid, "root", "r0")
    tip_main = st.append_thought(sid, "mainline", "m1")
    alt_tip = st.fork(sid, branch_name="alt", from_node_id=tip_main)
    st.checkout_branch(sid, "alt")
    st.append_thought(sid, "alternate idea", "a1")
    st.merge_into_current(sid, other_branch="main", summary="resolved: take alt")
    head = st.get_head(sid)
    node = st.get_node(head)
    assert node.kind == "merge"
    st.close()
