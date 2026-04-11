from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from honeyhex.eval.tables import summarize_tabular_rows
from honeyhex.llm.gateway import LlmGateway
from honeyhex.llm.schemas import ValidatorVerdict
from honeyhex.registry.db import reset_engine


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HONEYHEX_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    reset_engine()
    from honeyhex.api.app import create_app

    with TestClient(create_app()) as client:
        yield client


@pytest.mark.llm
def test_gateway_parses_litellm_response() -> None:
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content='{"approved": true, "reason": "metadata looks consistent"}',
            ),
        ),
    ]
    with patch("litellm.completion", return_value=mock_resp):
        gw = LlmGateway(default_model="gpt-4o-mini")
        v = gw.complete_validator_json(
            [{"role": "user", "content": "{}"}],
        )
    assert v.approved is True
    assert "consistent" in v.reason


@pytest.mark.llm
def test_eval_summarize_tabular_rows() -> None:
    out = summarize_tabular_rows([{"a": 1, "b": "x"}, {"a": 3, "b": "y"}])
    assert out["n_rows"] == 2
    assert "a" in out["numeric_means"]


@pytest.mark.registry
@pytest.mark.llm
def test_llm_evaluate_endpoint_records_vote(api_client: TestClient) -> None:
    pr = api_client.post(
        "/api/v1/prs",
        json={
            "swarm_id": "default",
            "source_agent_id": "s",
            "target_agent_id": "t",
            "head_sha": "ab" * 20,
            "title": "t",
        },
    )
    assert pr.status_code == 200
    pr_id = pr.json()["id"]

    verdict = ValidatorVerdict(approved=True, reason="mock")

    with patch(
        "honeyhex.llm.validator_agent.evaluate_pull_request_dict",
        return_value=verdict,
    ):
        r = api_client.post(
            f"/api/v1/prs/{pr_id}/llm-evaluate",
            json={"model": "gpt-4o-mini", "validator_id": "validator-a"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["approved"] is True
    assert body["pull_request"]["votes"]["validator-a"] is True
