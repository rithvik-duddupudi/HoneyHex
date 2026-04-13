# src/honeytrail/db/store.py
from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path


class TrailStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        raw = (resources.files("honeytrail") / "db/schema.sql").read_text(encoding="utf-8")
        self._conn.executescript(raw)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
