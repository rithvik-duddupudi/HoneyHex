from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from honeyhex.cell.remotes import add_remote
from honeyhex.cell.scaffold import init_cell
from honeyhex.cli.doctor import run_doctor
from honeyhex.cli.plugins import register_plugin_commands
from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff
from honeyhex.inspect.core import iter_log
from honeyhex.validators.snapshot import audit_state_diff


def test_iter_log_since_excludes_future(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    mgr.commit("only", StateDiff(prompt="a"))
    now = datetime.now(tz=UTC)
    entries = iter_log(
        tmp_path,
        max_count=10,
        since=now + timedelta(days=1),
    )
    assert entries == []


def test_export_filters_pass_to_iter_log(tmp_path: Path) -> None:
    from honeyhex.adoption.export_ledger import export_markdown

    mgr = CommitManager(tmp_path)
    mgr.commit("hello world", StateDiff(prompt="x"))
    md = export_markdown(tmp_path, max_count=5, message_grep="hello")
    assert "hello" in md


def test_audit_finds_sk_pattern(tmp_path: Path) -> None:
    bad = StateDiff(prompt="sk-test12345678901234567890", scratchpad="")
    assert any(f.rule == "secret_sk_prefix" for f in audit_state_diff(bad))


def test_doctor_reports_python(tmp_path: Path) -> None:
    rep = run_doctor(tmp_path)
    assert "checks" in rep
    assert rep["ok"] is True


def test_peer_merge_combines_ledgers(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    init_cell(a, guided=True)
    init_cell(b, guided=True)
    CommitManager(b).commit("remote-only", StateDiff(prompt="from-b"))
    add_remote(a, "peer", b)
    from honeyhex.cell.peer_merge import merge_peer_ledger

    head = merge_peer_ledger(a, "peer", favor="ours")
    assert len(head) == 40


def test_plugin_entry_point_registers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ep = EntryPoint(
        name="dummy",
        group="honeyhex.plugins",
        value="dummy_hex_plugin:register",
    )
    monkeypatch.setattr(
        "honeyhex.cli.plugins._plugin_entry_points",
        lambda: [ep],
    )
    app = typer.Typer()

    @app.command("noop")
    def _noop() -> None:
        """Anchor subcommand so Typer stays in multi-command mode."""

    register_plugin_commands(app)
    runner = CliRunner()
    r = runner.invoke(app, ["plugin-smoke-test"], prog_name="hex")
    assert r.exit_code == 0
    assert "plugin-ok" in r.stdout
