from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from honeyhex.registry.db import reset_engine

pytestmark = pytest.mark.registry


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HONEYHEX_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    reset_engine()
    from honeyhex.api.app import create_app

    with TestClient(create_app()) as tc:
        yield tc


def test_status_and_pr_quorum_flow(client: TestClient) -> None:
    r0 = client.get("/api/v1/status", params={"swarm_id": "default"})
    assert r0.status_code == 200
    body0 = r0.json()
    assert body0["swarm"]["id"] == "default"

    pr = client.post(
        "/api/v1/prs",
        json={
            "swarm_id": "default",
            "source_agent_id": "agent-a",
            "target_agent_id": "agent-b",
            "head_sha": "deadbeef" * 5,
            "title": "test pr",
        },
    )
    assert pr.status_code == 200
    pr_id = pr.json()["id"]

    for vid in ("validator-a", "validator-b"):
        v = client.post(
            f"/api/v1/prs/{pr_id}/votes",
            json={"validator_id": vid, "approved": True},
        )
        assert v.status_code == 200

    bad = client.post(
        f"/api/v1/prs/{pr_id}/votes",
        json={"validator_id": "not-a-validator", "approved": True},
    )
    assert bad.status_code == 400

    m = client.post(f"/api/v1/prs/{pr_id}/merge")
    assert m.status_code == 200
    assert m.json()["status"] == "merged"


def test_blackboard_order(client: TestClient) -> None:
    a = client.post(
        "/api/v1/blackboard/append",
        json={"swarm_id": "default", "agent_id": "a1", "payload": {"x": 1}},
    )
    assert a.status_code == 200
    b = client.post(
        "/api/v1/blackboard/append",
        json={"swarm_id": "default", "agent_id": "a2", "payload": {"x": 2}},
    )
    assert b.status_code == 200
    lst = client.get("/api/v1/blackboard", params={"swarm_id": "default"})
    assert lst.status_code == 200
    rows = lst.json()
    assert [r["lamport"] for r in rows] == [1, 2]
