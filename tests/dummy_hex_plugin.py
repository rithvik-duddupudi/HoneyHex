"""Test-only plugin: registered via patched entry points."""

from __future__ import annotations

import typer

_called = False


def register(app: typer.Typer) -> None:
    global _called
    _called = True

    @app.command("plugin-smoke-test")
    def _smoke() -> None:
        typer.echo("plugin-ok")
