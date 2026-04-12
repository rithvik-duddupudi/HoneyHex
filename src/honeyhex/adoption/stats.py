from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from honeyhex.inspect.core import read_snapshot_at
from honeyhex.ledger.git_store import HoneyHexLedger


def ledger_stats(cell_root: Path) -> dict[str, Any]:
    repo = HoneyHexLedger(cell_root).repo()
    by_day: Counter[str] = Counter()
    prompt_chars = 0
    scratch_chars = 0
    snapshots = 0
    for c in repo.iter_commits():
        dt = datetime.fromtimestamp(c.committed_date, tz=UTC)
        by_day[dt.strftime("%Y-%m-%d")] += 1
        _rev, snap = read_snapshot_at(cell_root, c.hexsha)
        if snap is not None:
            snapshots += 1
            prompt_chars += len(snap.prompt)
            scratch_chars += len(snap.scratchpad)
    total = sum(by_day.values())
    ratio = None
    if prompt_chars + scratch_chars > 0:
        ratio = round(prompt_chars / (prompt_chars + scratch_chars), 4)
    return {
        "commits": total,
        "commits_by_day": dict(sorted(by_day.items())),
        "snapshots_with_payload": snapshots,
        "prompt_chars": prompt_chars,
        "scratch_chars": scratch_chars,
        "prompt_to_scratch_char_ratio": ratio,
    }
