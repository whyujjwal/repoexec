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
