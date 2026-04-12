from __future__ import annotations

import json
from pathlib import Path

from honeyhex.adoption.search import search_ledger
from honeyhex.adoption.stats import ledger_stats
from honeyhex.adoption.validate import validate_cell
from honeyhex.branching.experiment import (
    experiment_branch_name,
    experiment_merge,
    experiment_start,
    list_experiment_branches,
)
from honeyhex.cell.config import load_cell_config
from honeyhex.cell.scaffold import init_cell
from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff


def test_config_json_persists_schema_version(tmp_path: Path) -> None:
    hh = tmp_path / ".honeyhex"
    hh.mkdir(parents=True)
    (hh / "config.json").write_text(
        '{"default_branch": "main", "hooks_mode": "off", "hooks": {}}',
        encoding="utf-8",
    )
    load_cell_config(tmp_path)
    data = json.loads((hh / "config.json").read_text(encoding="utf-8"))
    assert data.get("schema_version") == 1


def test_guided_init_records_first_thought(tmp_path: Path) -> None:
    out = init_cell(tmp_path, guided=True)
    assert out.get("guided") == "true"
    assert "hint_next" in out
    repo = CommitManager(tmp_path).ensure_ledger()
    msg = repo.head.commit.message
    if isinstance(msg, bytes):
        msg = msg.decode("utf-8", errors="replace")
    assert msg.strip().startswith("HoneyHex: first thought")


def test_search_python_fallback(tmp_path: Path) -> None:
    hh = tmp_path / ".honeyhex"
    hh.mkdir()
    (hh / "thoughts").mkdir(parents=True)
    (hh / "thoughts" / "note.txt").write_text("unique_needle_xyz\n", encoding="utf-8")
    code, out = search_ledger(tmp_path, "unique_needle_xyz")
    assert code == 0
    assert "unique_needle_xyz" in out


def test_stats_counts(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    mgr.commit("a", StateDiff(prompt="pp", scratchpad="ss"))
    st = ledger_stats(tmp_path)
    assert st["commits"] == 1
    assert st["prompt_chars"] == 2
    assert st["scratch_chars"] == 2


def test_validate_ok(tmp_path: Path) -> None:
    CommitManager(tmp_path).commit("x", StateDiff())
    ok, errs = validate_cell(tmp_path)
    assert ok is True
    assert errs == []


def test_validate_missing_cell(tmp_path: Path) -> None:
    ok, errs = validate_cell(tmp_path)
    assert ok is False
    assert errs


def test_experiment_branch_naming() -> None:
    assert experiment_branch_name("My Test") == "honeyhex/exp/my-test"


def test_experiment_start_and_merge(tmp_path: Path) -> None:
    init_cell(tmp_path, guided=True)
    experiment_start(tmp_path, "try-a")
    assert "honeyhex/exp/try-a" in list_experiment_branches(tmp_path)
    head = experiment_merge(tmp_path)
    assert len(head) == 40
