from __future__ import annotations

from pathlib import Path

from honeyhex.cell.config import load_cell_config
from honeyhex.ledger.git_store import HoneyHexLedger


def validate_cell(cell_root: Path) -> tuple[bool, list[str]]:
    errs: list[str] = []
    root = cell_root.resolve()
    hh = root / ".honeyhex"
    if not hh.is_dir():
        errs.append("missing .honeyhex directory")
        return False, errs
    if not (hh / ".git").is_dir():
        errs.append("missing .honeyhex/.git (ledger not initialized)")
    try:
        load_cell_config(root)
    except Exception as e:  # noqa: BLE001 — surface parse errors to user
        errs.append(f"invalid cell config: {e}")
    try:
        HoneyHexLedger(root).repo()
    except Exception as e:  # noqa: BLE001
        errs.append(f"ledger repo: {e}")
    return len(errs) == 0, errs
