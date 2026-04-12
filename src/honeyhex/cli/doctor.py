from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from honeyhex.cell.config import CURRENT_SCHEMA_VERSION, load_cell_config
from honeyhex.ledger.git_store import HoneyHexLedger


def _check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail}


def run_doctor(cell: Path | None) -> dict[str, Any]:
    """Environment and cell readiness checks (no network)."""
    root = (cell or Path.cwd()).resolve()
    checks: list[dict[str, Any]] = []

    v = sys.version_info
    checks.append(
        _check(
            "python_version",
            v >= (3, 12),
            f"{v.major}.{v.minor}.{v.micro}",
        ),
    )

    spec = importlib.util.find_spec("redis")
    checks.append(
        _check(
            "redis_extra",
            spec is not None,
            "import redis" if spec else "pip install 'honeyhex[redis]'",
        ),
    )

    spec_llm = importlib.util.find_spec("litellm")
    checks.append(
        _check(
            "llm_extra",
            spec_llm is not None,
            "import litellm" if spec_llm else "pip install 'honeyhex[llm]'",
        ),
    )

    rg = shutil.which("rg")
    rg_detail = rg or "not on PATH (hex search uses Python fallback)"
    checks.append(_check("ripgrep", rg is not None, rg_detail))

    try:
        r = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        git_out = (r.stdout or "").strip() or "git missing"
        checks.append(_check("git_cli", r.returncode == 0, git_out))
    except (OSError, subprocess.TimeoutExpired) as e:
        checks.append(_check("git_cli", False, str(e)))

    hh = root / ".honeyhex"
    if not hh.is_dir():
        msg = "no .honeyhex yet (optional; run hex cell init)"
        checks.append(_check("honeyhex_cell", True, msg))
    else:
        checks.append(_check("honeyhex_dir", True, str(hh)))
        git_ok = (hh / ".git").is_dir()
        git_msg = "ledger repo ok" if git_ok else "missing .honeyhex/.git"
        checks.append(_check("honeyhex_git", git_ok, git_msg))
        if git_ok:
            try:
                cfg = load_cell_config(root)
                checks.append(
                    _check(
                        "cell_config",
                        True,
                        (
                            f"schema_version={cfg.schema_version} "
                            f"(current {CURRENT_SCHEMA_VERSION})"
                        ),
                    ),
                )
            except Exception as e:  # noqa: BLE001
                checks.append(_check("cell_config", False, str(e)))
            try:
                HoneyHexLedger(root).repo()
            except Exception as e:  # noqa: BLE001
                checks.append(_check("ledger_repo_open", False, str(e)))
            else:
                checks.append(_check("ledger_repo_open", True, "GitPython ok"))

    base_ok = all(
        c["ok"] for c in checks if c["name"] in {"python_version", "git_cli"}
    )
    if hh.is_dir():
        base_ok = base_ok and all(
            c["ok"]
            for c in checks
            if c["name"]
            in {"honeyhex_git", "cell_config", "ledger_repo_open"}
        )
    return {"cell": str(root), "checks": checks, "ok": base_ok}
