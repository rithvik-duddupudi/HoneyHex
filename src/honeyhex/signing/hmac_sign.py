from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

from honeyhex.ledger.git_store import HoneyHexLedger


def _signing_key() -> bytes:
    raw = os.environ.get("HONEYHEX_SIGNING_KEY", "").strip()
    if not raw:
        msg = "set HONEYHEX_SIGNING_KEY to a shared secret (UTF-8 string)"
        raise ValueError(msg)
    return raw.encode("utf-8")


def _payload_for_commit(cell_root: Path, commit_sha: str) -> bytes:
    ledger = HoneyHexLedger(cell_root)
    repo = ledger.repo()
    cat = repo.git.cat_file("commit", commit_sha)
    return cat.encode("utf-8") if isinstance(cat, str) else bytes(cat)


def sign_commit(cell_root: Path, commit_sha: str) -> Path:
    """Write signature file: HMAC-SHA256 over `git cat-file commit <sha>`."""
    key = _signing_key()
    payload = _payload_for_commit(cell_root, commit_sha)
    digest = hmac.new(key, payload, hashlib.sha256).hexdigest()
    honeyhex = HoneyHexLedger(cell_root).honeyhex_path
    sig_dir = honeyhex / "signatures"
    sig_dir.mkdir(parents=True, exist_ok=True)
    path = sig_dir / f"{commit_sha}.sig"
    path.write_text(f"sha256={digest}\n", encoding="utf-8")
    return path


def verify_commit(cell_root: Path, commit_sha: str) -> bool:
    honeyhex = HoneyHexLedger(cell_root).honeyhex_path
    path = honeyhex / "signatures" / f"{commit_sha}.sig"
    if not path.is_file():
        return False
    line = path.read_text(encoding="utf-8").strip()
    if not line.startswith("sha256="):
        return False
    expected = line.split("=", 1)[1].strip()
    try:
        key = _signing_key()
    except ValueError:
        return False
    payload = _payload_for_commit(cell_root, commit_sha)
    digest = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)
