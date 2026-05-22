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
