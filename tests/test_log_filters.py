from __future__ import annotations

import json
from pathlib import Path

from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff
from honeyhex.inspect.core import iter_log, log_as_json


def test_hex_log_grep_filters_messages(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    mgr.commit("alpha one", StateDiff(prompt="a"))
    mgr.commit("beta two", StateDiff(prompt="b"))
    entries = iter_log(tmp_path, max_count=10, message_grep="beta")
    assert len(entries) == 1
    assert "beta" in entries[0].message


def test_log_as_json_passes_filters(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    mgr.commit("only", StateDiff())
    data = json.loads(log_as_json(tmp_path, max_count=5, message_grep="only"))
    assert len(data) == 1
