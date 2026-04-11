from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from honeyhex.cell.config import CellConfig, load_cell_config
from honeyhex.ledger.git_store import HoneyHexLedger
from honeyhex.mesh.publish import read_head_sha


@dataclass(frozen=True)
class HookContext:
    cell_root: Path
    hook_name: str


@dataclass(frozen=True)
class HookResult:
    returncode: int
    stdout: str
    stderr: str


def effective_hooks_mode(cell_root: Path) -> Literal["off", "safe", "full"]:
    env = os.environ.get("HONEYHEX_HOOKS")
    if env in ("off", "safe", "full"):
        return env  # type: ignore[return-value]
    return load_cell_config(cell_root).hooks_mode


def _hook_script(cell_root: Path, cfg: CellConfig, name: str) -> Path | None:
    rel = cfg.hooks.get(name)
    if not rel:
        return None
    path = (HoneyHexLedger(cell_root).honeyhex_path / rel).resolve()
    root = HoneyHexLedger(cell_root).honeyhex_path.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path.is_file() else None


def run_named_hook(ctx: HookContext) -> HookResult:
    """
    Run a configured hook script. If no script is configured, returns success (0).
    """
    mode = effective_hooks_mode(ctx.cell_root)
    if mode == "off":
        return HookResult(0, "", "")
    cfg = load_cell_config(ctx.cell_root)
    script = _hook_script(ctx.cell_root, cfg, ctx.hook_name)
    if script is None:
        return HookResult(0, "", "")
    if mode == "safe" and ctx.hook_name not in (
        "pre-thought",
        "post-thought",
    ):
        return HookResult(0, "", "")
    honeyhex = HoneyHexLedger(ctx.cell_root).honeyhex_path
    env = os.environ.copy()
    env["HONEYHEX_CELL"] = str(ctx.cell_root.resolve())
    env["HONEYHEX_HONEYHEX"] = str(honeyhex.resolve())
    env["HONEYHEX_HOOK"] = ctx.hook_name
    try:
        env["HONEYHEX_HEAD"] = read_head_sha(ctx.cell_root)
    except Exception:
        env["HONEYHEX_HEAD"] = ""
    proc = subprocess.run(
        [os.environ.get("SHELL", "/bin/sh"), str(script)],
        cwd=honeyhex,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return HookResult(proc.returncode, proc.stdout or "", proc.stderr or "")


def echo_hook_output(res: HookResult, *, err_stream: bool = False) -> None:
    if res.stdout:
        sys.stdout.write(res.stdout)
    if res.stderr:
        (sys.stderr if err_stream else sys.stdout).write(res.stderr)
