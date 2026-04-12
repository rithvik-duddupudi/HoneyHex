from __future__ import annotations

import tempfile
from pathlib import Path

import typer
from typer.testing import CliRunner

from honeyhex.adoption.scrub import scrub_text
from honeyhex.cli.adoption_cmds import register_adoption_commands


def test_scrub_matches_golden_fixture() -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "scrub"
    raw = (base / "leaky.txt").read_text(encoding="utf-8")
    want = (base / "leaky_expected.txt").read_text(encoding="utf-8")
    assert scrub_text(raw) == want


def test_scrub_dry_run_rejects_in_place() -> None:
    app = typer.Typer()
    register_adoption_commands(app)
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"x")
        p = f.name
    try:
        r = runner.invoke(
            app,
            ["scrub", p, "-i", "--dry-run"],
            prog_name="hex",
        )
        assert r.exit_code == 2
    finally:
        Path(p).unlink(missing_ok=True)
