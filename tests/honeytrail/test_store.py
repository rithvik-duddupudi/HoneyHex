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
