import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from repoexec.api import create_app


@pytest.fixture
def policy_file(tmp_path: Path) -> Path:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "allow": ["echo *", "blocked *"],
                "deny": ["rm *"],
                "require_approval": ["git push*"],
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def client(tmp_path: Path, policy_file: Path):
    trace_path = tmp_path / "traces.jsonl"
    app = create_app(policy_path=policy_file, trace_path=trace_path)
    return TestClient(app)


def test_healthz(client: TestClient):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_allowed_run_executes_and_persists(client: TestClient):
    response = client.post(
        "/runs",
        json={"workspace": ".", "command": "echo hello", "metadata": {"agent": "test"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "allowed"
    assert body["exit_code"] == 0
    assert "hello" in body["stdout"]

    run_id = body["run_id"]
    trace = client.get(f"/runs/{run_id}")
    assert trace.status_code == 200
    assert trace.json()["metadata"] == {"agent": "test"}


def test_denied_run_returns_structured_response(client: TestClient):
    response = client.post("/runs", json={"workspace": ".", "command": "rm -rf /tmp/x"})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "denied"
    assert body["exit_code"] is None
    assert body["matched_rule"] == "rm *"
    assert body["rule_category"] == "deny"
    assert "deny rule" in body["policy_reason"]


def test_approval_required_run_is_blocked(client: TestClient):
    response = client.post(
        "/runs",
        json={"workspace": ".", "command": "git push origin main"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "approval_required"
    assert body["exit_code"] is None
    assert body["matched_rule"] == "git push*"
    assert "require_approval" in body["policy_reason"]


def test_get_unknown_run_returns_404(client: TestClient):
    response = client.get("/runs/does-not-exist")
    assert response.status_code == 404


def test_timeout_override(client: TestClient):
    response = client.post(
        "/runs",
        json={
            "workspace": ".",
            "command": "echo fast",
            "timeout_seconds": 60,
        },
    )
    assert response.status_code == 200
    assert response.json()["stdout"].strip() == "fast"


def test_list_runs_returns_recent_records(client: TestClient):
    first = client.post("/runs", json={"workspace": ".", "command": "echo one"})
    second = client.post("/runs", json={"workspace": ".", "command": "echo two"})
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.get("/runs?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2
    assert body[0]["command"] == "echo two"
    assert body[1]["command"] == "echo one"


def test_list_runs_filters_by_decision(client: TestClient):
    client.post("/runs", json={"workspace": ".", "command": "echo ok"})
    client.post("/runs", json={"workspace": ".", "command": "rm -rf /tmp/x"})

    response = client.get("/runs?decision=denied")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert all(record["decision"] == "denied" for record in body)


def test_replay_run_reexecutes_allowed_command(client: TestClient):
    create = client.post("/runs", json={"workspace": ".", "command": "echo replay-me"})
    assert create.status_code == 200
    run_id = create.json()["run_id"]

    replay = client.post(f"/runs/{run_id}/replay")
    assert replay.status_code == 200
    body = replay.json()
    assert body["decision"] == "allowed"
    assert "replay-me" in body["stdout"]
    assert body["run_id"] != run_id

    trace = client.get(f"/runs/{body['run_id']}")
    assert trace.status_code == 200
    assert trace.json()["metadata"]["replayed_from"] == run_id


def test_replay_unknown_run_returns_404(client: TestClient):
    response = client.post("/runs/missing-run/replay")
    assert response.status_code == 404


def test_explain_endpoint_returns_policy_evaluation(client: TestClient):
    response = client.get("/explain", params={"command": "rm -rf /tmp/x"})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "denied"
    assert body["matched_rule"] == "rm *"


def test_invalid_workspace_returns_400(client: TestClient, tmp_path: Path):
    missing = tmp_path / "missing-workspace"
    response = client.post(
        "/runs",
        json={"workspace": str(missing), "command": "echo hello"},
    )
    assert response.status_code == 400
