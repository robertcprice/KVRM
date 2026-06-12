import json

import pytest
from fastapi.testclient import TestClient

from kvrm_core.domain_dir import _SCAFFOLD_CASES, _SCAFFOLD_CONFIG, _SCAFFOLD_REGISTRY, _SCAFFOLD_TRAIN
from kvrm_server import create_app


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(data_root=tmp_path / "data", api_keys={"test-key"}))


HEADERS = {"X-API-Key": "test-key"}


def _upload(client, name="loan-review", **overrides):
    payload = {
        "name": name,
        "registry": dict(_SCAFFOLD_REGISTRY, registry_name=name.replace("-", "_")),
        "train_cases": _SCAFFOLD_TRAIN,
        "cases": _SCAFFOLD_CASES,
        "config": _SCAFFOLD_CONFIG,
    }
    payload.update(overrides)
    return client.post("/domains", json=payload, headers=HEADERS)


def test_health_open(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["auth"] is True


def test_auth_required(client):
    assert client.get("/domains").status_code == 401
    assert client.get("/domains", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/domains", headers=HEADERS).status_code == 200


def test_upload_route_eval_audit_workflow(client):
    response = _upload(client)
    assert response.status_code == 201, response.text
    assert "approve_request" in response.json()["actions"]

    # duplicate without overwrite -> conflict
    assert _upload(client).status_code == 409

    # train
    response = client.post("/domains/loan-review/train", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["train_accuracy"] == 1.0

    # supported input executes
    response = client.post(
        "/domains/loan-review/route",
        json={"features": {"risk_level": "low", "amount": 250.0, "account_verified": True}},
        headers=HEADERS,
    )
    assert response.status_code == 200
    decision = response.json()
    assert decision["selected_action_id"] == "approve_request"
    assert decision["final_status"] == "executed"
    assert decision["audit_id"] >= 1

    # out-of-envelope input fails closed
    response = client.post(
        "/domains/loan-review/route",
        json={"features": {"risk_level": "low", "amount": 9e9, "account_verified": True}},
        headers=HEADERS,
    )
    decision = response.json()
    assert decision["selected_action_id"] not in ("approve_request", "deny_request")
    assert decision["final_status"] in ("fallback_executed", "fail_closed", "abstained")

    # eval over the uploaded cases
    response = client.post("/domains/loan-review/eval", json={}, headers=HEADERS)
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["semantic_correctness_rate"] == 1.0
    assert metrics["false_accept_rate"] == 0.0

    # audit log has both routed decisions, digest-bound
    response = client.get("/domains/loan-review/audit", headers=HEADERS)
    decisions = response.json()["decisions"]
    assert len(decisions) >= 2
    assert all(d["audit_record"]["registry_digest"] for d in decisions)


def test_invalid_registry_rejected(client):
    bad_registry = dict(_SCAFFOLD_REGISTRY, registry_name="bad")
    bad_registry = json.loads(json.dumps(bad_registry))
    bad_registry["actions"] = bad_registry["actions"] + [bad_registry["actions"][0]]  # duplicate id
    response = _upload(client, name="bad", registry=bad_registry)
    assert response.status_code == 422


def test_unknown_domain_404(client):
    assert client.get("/domains/nope", headers=HEADERS).status_code == 404
    assert client.post("/domains/nope/route", json={"features": {}}, headers=HEADERS).status_code == 404
