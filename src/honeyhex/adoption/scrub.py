from __future__ import annotations

import re
from pathlib import Path

# Opinionated patterns — opt-in via `hex scrub`; not a full secret scanner.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-[a-zA-Z0-9]{10,}"), "[REDACTED_SK_KEY]"),
    (re.compile(r"Bearer\s+\S+"), "Bearer [REDACTED]"),
    (
        re.compile(
            r"-----BEGIN [A-Z ]+PRIVATE KEY-----"
            r"[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----",
        ),
        "[REDACTED_PEM]",
    ),
]


def scrub_text(text: str) -> str:
    out = text
    for rx, repl in _PATTERNS:
        out = rx.sub(repl, out)
    return out


def scrub_path(path: Path) -> str:
    return scrub_text(path.read_text(encoding="utf-8", errors="replace"))
