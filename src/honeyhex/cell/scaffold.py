from __future__ import annotations

import stat
from pathlib import Path

from honeyhex.cell.config import CellConfig, config_path_json, save_cell_config
from honeyhex.commit.manager import CommitManager
from honeyhex.ledger.git_store import HoneyHexLedger


def init_cell(cell_root: Path, *, hook_stubs: bool = False) -> dict[str, str]:
    """
    Ensure `.honeyhex` exists with optional `config.json` and hook script stubs.
    Does not create an initial thought-commit.
    """
    root = cell_root.resolve()
    mgr = CommitManager(root)
    mgr.ensure_ledger()
    cfg_path = config_path_json(root)
    if not cfg_path.is_file():
        save_cell_config(root, CellConfig())
    honeyhex = HoneyHexLedger(root).honeyhex_path
    created: dict[str, str] = {"honeyhex": str(honeyhex)}
    if hook_stubs:
        hooks_dir = honeyhex / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        pre = hooks_dir / "pre-thought.sh"
        pre.write_text(
            "#!/bin/sh\n"
            "# pre-thought — exit non-zero to abort `hex commit`\n"
            'echo "pre-thought ok"\n',
            encoding="utf-8",
        )
        pre.chmod(pre.stat().st_mode | stat.S_IXUSR)
        post = hooks_dir / "post-thought.sh"
        post.write_text(
            "#!/bin/sh\n# post-thought — runs after commit\n"
            'echo "post-thought ok"\n',
            encoding="utf-8",
        )
        post.chmod(post.stat().st_mode | stat.S_IXUSR)
        cfg = CellConfig(
            hooks_mode="full",
            hooks={
                "pre-thought": "hooks/pre-thought.sh",
                "post-thought": "hooks/post-thought.sh",
            },
        )
        save_cell_config(root, cfg)
        created["pre-thought"] = str(pre)
        created["post-thought"] = str(post)
    return created
