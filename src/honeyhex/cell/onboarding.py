from __future__ import annotations

from pathlib import Path

from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff


def run_guided_first_run(cell_root: Path) -> dict[str, str]:
    """
    After `.honeyhex` exists: create one starter thought-commit and return hints.
    """
    mgr = CommitManager(cell_root)
    mgr.commit(
        "HoneyHex: first thought (guided)",
        StateDiff(
            prompt="hello from HoneyHex",
            scratchpad="guided tour — edit and run `hex commit` for real work",
        ),
    )
    return {
        "next": "Try: hex log --oneline -n 5",
        "show": "hex show",
        "commit": "hex commit -m \"my note\" --prompt \"…\" --scratchpad \"…\"",
    }
