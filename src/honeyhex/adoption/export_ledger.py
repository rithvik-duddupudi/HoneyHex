from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from honeyhex.inspect.core import iter_log, read_snapshot_at


def export_markdown(
    cell_root: Path,
    *,
    max_count: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    message_grep: str | None = None,
    after_tag: str | None = None,
) -> str:
    entries = list(
        iter_log(
            cell_root,
            max_count=max_count,
            since=since,
            until=until,
            message_grep=message_grep,
            after_tag=after_tag,
        ),
    )
    entries_chrono = list(reversed(entries))
    lines: list[str] = ["# HoneyHex export", ""]
    for e in entries_chrono:
        title = e.message.splitlines()[0] if e.message else "(no message)"
        lines.append(f"## `{e.short}` — {title}")
        lines.append("")
        _rev, snap = read_snapshot_at(cell_root, e.hexsha)
        if snap is not None:
            lines.append("```json")
            lines.append(json.dumps(snap.model_dump(), indent=2))
            lines.append("```")
        else:
            lines.append("_(no snapshot at this revision)_")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_html(
    cell_root: Path,
    *,
    max_count: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    message_grep: str | None = None,
    after_tag: str | None = None,
) -> str:
    entries = list(
        iter_log(
            cell_root,
            max_count=max_count,
            since=since,
            until=until,
            message_grep=message_grep,
            after_tag=after_tag,
        ),
    )
    entries_chrono = list(reversed(entries))
    out: list[str] = [
        "<!DOCTYPE html>",
        "<html lang='en'><head><meta charset='utf-8'><title>HoneyHex export</title>",
        "<style>body{font-family:system-ui,sans-serif;"
        "max-width:48rem;margin:1rem auto;}",
        "pre{background:#f4f4f4;padding:0.75rem;overflow:auto;}</style></head><body>",
        "<h1>HoneyHex export</h1>",
    ]
    for e in entries_chrono:
        title = e.message.splitlines()[0] if e.message else "(no message)"
        out.append(f"<h2>{html.escape(e.short)} — {html.escape(title)}</h2>")
        _rev, snap = read_snapshot_at(cell_root, e.hexsha)
        if snap is not None:
            body = json.dumps(snap.model_dump(), indent=2)
            out.append(f"<pre>{html.escape(body)}</pre>")
        else:
            out.append("<p><em>(no snapshot at this revision)</em></p>")
    out.append("</body></html>")
    return "\n".join(out)
