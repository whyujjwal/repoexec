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


def test_approval_required_run_is_blocked(client: TestClient):
    response = client.post(
        "/runs",
        json={"workspace": ".", "command": "git push origin main"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "approval_required"
    assert body["exit_code"] is None


def test_get_unknown_run_returns_404(client: TestClient):
    response = client.get("/runs/does-not-exist")
    assert response.status_code == 404
