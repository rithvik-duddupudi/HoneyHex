from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from honeyhex.bundle.io import create_bundle, replay_bundle
from honeyhex.cell.config import load_cell_config
from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff
from honeyhex.inspect.core import diff_as_json, git_blame_as_json, log_as_json
from honeyhex.mesh.outbox import enqueue_pr, sync_outbox
from honeyhex.mesh.publish import read_head_sha
from honeyhex.signing.hmac_sign import sign_commit, verify_commit


def test_log_and_diff_json(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    mgr.commit("a", StateDiff(prompt="1"))
    mgr.commit("b", StateDiff(prompt="2"))
    logj = json.loads(log_as_json(tmp_path, max_count=10))
    assert len(logj) == 2
    diffj = json.loads(diff_as_json(tmp_path, None, None))
    assert diffj["format"] == "git-unified"
    assert "text" in diffj


def test_bundle_roundtrip(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    m = CommitManager(a)
    m.commit("m1", StateDiff(prompt="p1"))
    m.commit("m2", StateDiff(prompt="p2"))
    z = tmp_path / "x.zip"
    create_bundle(a, z)
    replay_bundle(b, z)
    txt = (b / ".honeyhex" / "thoughts" / "snapshot.json").read_text()
    assert "p2" in txt


def test_sign_verify_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HONEYHEX_SIGNING_KEY", "test-secret-key-for-hmac")
    mgr = CommitManager(tmp_path)
    mgr.commit("s", StateDiff(prompt="z"))
    sha = read_head_sha(tmp_path)
    sign_commit(tmp_path, sha)
    assert verify_commit(tmp_path, sha) is True


def test_outbox_sync_mocked_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HONEYHEX_REGISTRY_URL", "http://127.0.0.1:9")

    class _H:
        def post(self, *_a: object, **_k: object) -> MagicMock:
            r = MagicMock()
            r.json.return_value = {"id": "pr1", "status": "open"}
            r.raise_for_status = MagicMock()
            return r

    monkeypatch.setattr("honeyhex.mesh.registry_pr._httpx_mod", lambda: _H())

    mgr = CommitManager(tmp_path)
    mgr.commit("x", StateDiff(prompt="q"))
    enqueue_pr(
        tmp_path,
        source="a1",
        target="a2",
        swarm_id="default",
        title="t",
    )
    out = sync_outbox(tmp_path)
    assert out["synced"] == 1
    assert out["results"][0]["ok"] is True


def test_config_toml_precedence(tmp_path: Path) -> None:
    hh = tmp_path / ".honeyhex"
    hh.mkdir(parents=True)
    toml = (
        'default_branch = "main"\n'
        'hooks_mode = "off"\n\n[hooks]\n'
        'pre-thought = "hooks/x.sh"\n'
    )
    (hh / "config.toml").write_text(toml, encoding="utf-8")
    cfg = load_cell_config(tmp_path)
    assert cfg.hooks.get("pre-thought") == "hooks/x.sh"


def test_blame_json_parses(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    mgr.commit("b", StateDiff(prompt="trace"))
    raw = git_blame_as_json(tmp_path, None)
    data = json.loads(raw)
    assert data["path"] == "thoughts/snapshot.json"
    assert "lines" in data


@pytest.mark.skipif(
    not os.environ.get("HONEYHEX_SLOW_TESTS"),
    reason="set HONEYHEX_SLOW_TESTS=1 for N-commit smoke",
)
def test_log_json_many_commits(tmp_path: Path) -> None:
    mgr = CommitManager(tmp_path)
    n = int(os.environ.get("HONEYHEX_SLOW_COMMIT_COUNT", "1000"))
    for i in range(n):
        mgr.commit(f"c{i}", StateDiff(prompt=str(i)))
    arr = json.loads(log_as_json(tmp_path, max_count=None))
    assert len(arr) == n
