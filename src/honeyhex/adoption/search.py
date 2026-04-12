from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from honeyhex.ledger.git_store import HoneyHexLedger


def search_ledger(cell_root: Path, pattern: str) -> tuple[int, str]:
    """
    Search under `.honeyhex/` (excluding `.git`).
    Returns (exit_code, combined stdout/stderr text).
    Uses ripgrep when available, else a small Python scanner (UTF-8).
    """
    hh = HoneyHexLedger(cell_root).honeyhex_path
    if not hh.is_dir():
        return 1, ""

    rg = shutil.which("rg")
    if rg:
        cmd = [
            rg,
            "-n",
            "--color",
            "never",
            "--hidden",
            "--glob",
            "!.git/**",
            pattern,
            str(hh),
        ]
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        out = (r.stdout or "") + (r.stderr or "")
        # ripgrep uses exit 1 for "no matches" which is still a successful run
        rc = 0 if r.returncode in (0, 1) else r.returncode
        return rc, out.rstrip()

    return _search_python(hh, pattern)


def _search_python(honeyhex: Path, pattern: str) -> tuple[int, str]:
    lines_out: list[str] = []
    matches = 0
    for path in sorted(honeyhex.rglob("*")):
        if ".git" in path.parts:
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                rel = path.relative_to(honeyhex)
                lines_out.append(f"{rel}:{i}:{line}")
                matches += 1
    text = "\n".join(lines_out)
    return (0 if matches else 1), text
