import json
from pathlib import Path

from typer.testing import CliRunner

from repoexec.cli import app


runner = CliRunner()


def test_explain_reports_denied_command(tmp_path: Path):
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps({"allow": ["echo *"], "deny": ["rm *"], "require_approval": []}),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["explain", "--command", "rm -rf /", "--policy", str(policy)])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["decision"] == "denied"
    assert body["matched_rule"] == "rm *"


def test_run_rejects_workspace_outside_root(tmp_path: Path):
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps({"allow": ["echo *"], "deny": [], "require_approval": []}),
        encoding="utf-8",
    )
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    trace = tmp_path / "traces.jsonl"

    result = runner.invoke(
        app,
        [
            "run",
            "--workspace",
            str(outside),
            "--command",
            "echo hello",
            "--policy",
            str(policy),
            "--trace",
            str(trace),
            "--workspace-root",
            str(root),
        ],
    )
    assert result.exit_code == 1
    body = json.loads(result.stdout)
    assert "outside allowed root" in body["error"]


def test_approve_and_run_with_token(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("REPOEXEC_APPROVAL_SECRET", "cli-test-secret")
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {"allow": ["echo *"], "deny": [], "require_approval": ["echo approve*"]}
        ),
        encoding="utf-8",
    )
    trace = tmp_path / "traces.jsonl"
    workspace = tmp_path / "repo"
    workspace.mkdir()

    approve = runner.invoke(
        app,
        [
            "approve",
            "--workspace",
            str(workspace),
            "--command",
            "echo approved",
        ],
    )
    assert approve.exit_code == 0
    token = json.loads(approve.stdout)["approval_token"]

    blocked = runner.invoke(
        app,
        [
            "run",
            "--workspace",
            str(workspace),
            "--command",
            "echo approved",
            "--policy",
            str(policy),
            "--trace",
            str(trace),
        ],
    )
    assert blocked.exit_code == 2
    assert json.loads(blocked.stdout)["decision"] == "approval_required"

    allowed = runner.invoke(
        app,
        [
            "run",
            "--workspace",
            str(workspace),
            "--command",
            "echo approved",
            "--policy",
            str(policy),
            "--trace",
            str(trace),
            "--approval-token",
            token,
        ],
    )
    assert allowed.exit_code == 0
    body = json.loads(allowed.stdout)
    assert body["decision"] == "allowed"
    assert body["stdout"].strip() == "approved"
    assert "approved via token" in body["policy_reason"]


def test_traces_list_compact_format(tmp_path: Path):
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps({"allow": ["echo *"], "deny": [], "require_approval": []}),
        encoding="utf-8",
    )
    trace = tmp_path / "traces.jsonl"
    workspace = tmp_path / "repo"
    workspace.mkdir()

    runner.invoke(
        app,
        [
            "run",
            "--workspace",
            str(workspace),
            "--command",
            "echo compact-list",
            "--policy",
            str(policy),
            "--trace",
            str(trace),
        ],
    )

    result = runner.invoke(
        app,
        [
            "traces",
            "list",
            "--trace",
            str(trace),
            "--format",
            "compact",
            "--command",
            "compact",
        ],
    )
    assert result.exit_code == 0
    assert "RUN ID" in result.stdout
    assert "compact-list" in result.stdout
    assert "allowed" in result.stdout


def test_traces_get_compact_format(tmp_path: Path):
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps({"allow": ["echo *"], "deny": [], "require_approval": []}),
        encoding="utf-8",
    )
    trace = tmp_path / "traces.jsonl"
    workspace = tmp_path / "repo"
    workspace.mkdir()

    run = runner.invoke(
        app,
        [
            "run",
            "--workspace",
            str(workspace),
            "--command",
            "echo compact-get",
            "--policy",
            str(policy),
            "--trace",
            str(trace),
        ],
    )
    run_id = json.loads(run.stdout)["run_id"]

    result = runner.invoke(
        app,
        [
            "traces",
            "get",
            "--run-id",
            run_id,
            "--trace",
            str(trace),
            "--format",
            "compact",
        ],
    )
    assert result.exit_code == 0
    assert f"Run ID:    {run_id}" in result.stdout
    assert "echo compact-get" in result.stdout
    assert "Stdout:" in result.stdout
