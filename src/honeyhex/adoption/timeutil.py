from __future__ import annotations

from datetime import UTC, datetime


def parse_iso_datetime(s: str | None) -> datetime | None:
    """Parse `--since` / `--until` values (date or full ISO-8601, UTC-normalized)."""
    if s is None or not str(s).strip():
        return None
    t = str(s).strip()
    if len(t) == 10 and t[4] == "-" and t[7] == "-":
        dt = datetime.fromisoformat(f"{t}T00:00:00+00:00")
        return dt.astimezone(UTC)
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
