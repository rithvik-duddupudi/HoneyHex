from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable


def _plugin_entry_points() -> Iterable[importlib.metadata.EntryPoint]:
    eps = importlib.metadata.entry_points()
    return eps.select(group="honeyhex.plugins")


def register_plugin_commands(app: object) -> None:
    """Load third-party Typer hooks registered under ``honeyhex.plugins``."""
    for ep in _plugin_entry_points():
        register = ep.load()
        if callable(register):
            register(app)
