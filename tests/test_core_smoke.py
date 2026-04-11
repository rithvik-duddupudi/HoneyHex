from __future__ import annotations


def test_cli_main_imports_without_registry_stack() -> None:
    """Core `pip install` can import the Typer CLI without SQLAlchemy or FastAPI."""
    import honeyhex.cli.main  # noqa: F401
