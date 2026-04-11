from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from honeyhex.cell.hooks import HookContext, run_named_hook
from honeyhex.mesh.publish import read_head_sha


def _httpx_mod() -> Any:
    try:
        import httpx
    except ImportError as e:
        msg = "Install registry extras: pip install 'honeyhex[registry]'"
        raise ImportError(msg) from e
    return httpx


def registry_url() -> str:
    return os.environ.get("HONEYHEX_REGISTRY_URL", "http://127.0.0.1:8765").rstrip("/")


def post_pr_to_registry(
    cell_root: Path,
    *,
    source: str,
    target: str,
    swarm_id: str,
    title: str,
    head_sha: str | None = None,
) -> dict[str, Any]:
    """
    Run `pre-push` hook, then POST /api/v1/prs.
    If head_sha is None, uses current `.honeyhex` HEAD.
    """
    root = cell_root.resolve()
    pre = run_named_hook(HookContext(root, "pre-push"))
    if pre.returncode != 0:
        detail = (pre.stderr or pre.stdout or "").strip()
        msg = f"pre-push hook failed (exit {pre.returncode})"
        if detail:
            msg = f"{msg}: {detail}"
        raise RuntimeError(msg)
    httpx = _httpx_mod()
    head = head_sha if head_sha is not None else read_head_sha(root)
    payload = {
        "swarm_id": swarm_id,
        "source_agent_id": source,
        "target_agent_id": target,
        "head_sha": head,
        "title": title or f"{source} -> {target}",
    }
    url = f"{registry_url()}/api/v1/prs"
    r = httpx.post(url, json=payload, timeout=30.0)
    r.raise_for_status()
    out: dict[str, Any] = r.json()
    return out
