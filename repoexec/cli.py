import json
from pathlib import Path

import typer
import uvicorn

from repoexec.config import DEFAULT_HOST, DEFAULT_POLICY_PATH, DEFAULT_PORT, DEFAULT_TRACE_PATH
from repoexec.models import PolicyDecision, TraceRecord, utc_now
from repoexec.policy import evaluate_policy, load_policy
from repoexec.runner import run_command
from repoexec.store import TraceStore

app = typer.Typer(help="RepoExec: policy-checked command execution with trace logging.")


@app.command()
def serve(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind."),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind."),
    policy: Path = typer.Option(DEFAULT_POLICY_PATH, help="Path to policy JSON file."),
    trace: Path = typer.Option(DEFAULT_TRACE_PATH, help="Path to JSONL trace log."),
) -> None:
    """Start the RepoExec HTTP API server."""
    from repoexec.api import create_app

    api_app = create_app(policy_path=policy, trace_path=trace)
    uvicorn.run(api_app, host=host, port=port)


@app.command()
def run(
    workspace: Path = typer.Option(..., help="Workspace directory for command execution."),
    command: str = typer.Option(..., help="Shell command to evaluate and optionally run."),
    policy: Path = typer.Option(DEFAULT_POLICY_PATH, help="Path to policy JSON file."),
    trace: Path = typer.Option(DEFAULT_TRACE_PATH, help="Path to JSONL trace log."),
) -> None:
    """Evaluate policy locally, run if allowed, and persist a trace record."""
    policy_obj = load_policy(policy)
    store = TraceStore(trace)
    run_id = TraceRecord.new_id()
    decision = evaluate_policy(policy_obj, command)

    if decision is PolicyDecision.DENIED:
        record = TraceRecord(
            run_id=run_id,
            timestamp=utc_now(),
            workspace=str(workspace),
            command=command,
            decision=decision,
        )
        store.append(record)
        typer.echo(json.dumps({"run_id": run_id, "decision": decision.value, "message": "denied"}))
        raise typer.Exit(code=1)

    if decision is PolicyDecision.APPROVAL_REQUIRED:
        record = TraceRecord(
            run_id=run_id,
            timestamp=utc_now(),
            workspace=str(workspace),
            command=command,
            decision=decision,
        )
        store.append(record)
        typer.echo(
            json.dumps(
                {
                    "run_id": run_id,
                    "decision": decision.value,
                    "message": "approval_required",
                }
            )
        )
        raise typer.Exit(code=2)

    result = run_command(workspace, command)
    record = TraceRecord(
        run_id=run_id,
        timestamp=utc_now(),
        workspace=str(workspace),
        command=command,
        decision=decision,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        stdout=result.stdout,
        stderr=result.stderr,
    )
    store.append(record)
    typer.echo(
        json.dumps(
            {
                "run_id": run_id,
                "decision": decision.value,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_ms": result.duration_ms,
            }
        )
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
