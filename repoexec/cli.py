import json
from pathlib import Path

import typer
import uvicorn

from repoexec.config import (
    DEFAULT_APPROVAL_SECRET_PATH,
    DEFAULT_HOST,
    DEFAULT_POLICY_PATH,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TRACE_PATH,
)
from repoexec.approval import ApprovalError, issue_approval_token, resolve_approval_secret
from repoexec.policy import evaluate_policy, load_policy
from repoexec.service import RunExecutionError, execute_run, replay_run
from repoexec.store import TraceStore

app = typer.Typer(help="RepoExec: policy-checked command execution with trace logging.")
traces_app = typer.Typer(help="Inspect persisted run traces.")
app.add_typer(traces_app, name="traces")


@app.command()
def serve(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind."),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind."),
    policy: Path = typer.Option(DEFAULT_POLICY_PATH, help="Path to policy JSON file."),
    trace: Path = typer.Option(DEFAULT_TRACE_PATH, help="Path to JSONL trace log."),
    workspace_root: Path | None = typer.Option(
        None,
        help="Require all workspaces to resolve inside this directory.",
    ),
    approval_secret: Path = typer.Option(
        DEFAULT_APPROVAL_SECRET_PATH,
        help="Path to the local HMAC secret file for approval tokens.",
    ),
) -> None:
    """Start the RepoExec HTTP API server."""
    from repoexec.api import create_app

    api_app = create_app(
        policy_path=policy,
        trace_path=trace,
        workspace_root=workspace_root,
        approval_secret_path=approval_secret,
    )
    uvicorn.run(api_app, host=host, port=port)


@app.command()
def approve(
    workspace: Path = typer.Option(..., help="Workspace the token authorizes."),
    command: str = typer.Option(..., help="Exact command the token authorizes."),
    secret_path: Path = typer.Option(
        DEFAULT_APPROVAL_SECRET_PATH,
        help="Path to the local HMAC secret file.",
    ),
    create_secret: bool = typer.Option(
        False,
        help="Create a local secret file if one does not exist.",
    ),
    ttl_seconds: int = typer.Option(
        3600,
        help="Token lifetime in seconds (0 for no expiry).",
    ),
) -> None:
    """Issue a local HMAC approval token for a workspace/command pair."""
    try:
        secret = resolve_approval_secret(
            secret_path=secret_path,
            create_if_missing=create_secret,
        )
        token = issue_approval_token(
            workspace=str(workspace),
            command=command,
            secret=secret,
            ttl_seconds=ttl_seconds if ttl_seconds > 0 else None,
        )
    except ApprovalError as exc:
        typer.echo(json.dumps({"error": str(exc)}))
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps({"approval_token": token}))


@app.command()
def run(
    workspace: Path = typer.Option(..., help="Workspace directory for command execution."),
    command: str = typer.Option(..., help="Shell command to evaluate and optionally run."),
    policy: Path = typer.Option(DEFAULT_POLICY_PATH, help="Path to policy JSON file."),
    trace: Path = typer.Option(DEFAULT_TRACE_PATH, help="Path to JSONL trace log."),
    timeout: int = typer.Option(
        DEFAULT_TIMEOUT_SECONDS,
        help="Maximum seconds before the command is terminated.",
    ),
    workspace_root: Path | None = typer.Option(
        None,
        help="Require the workspace to resolve inside this directory.",
    ),
    approval_token: str | None = typer.Option(
        None,
        help="HMAC approval token for require_approval commands.",
    ),
    approval_secret: Path = typer.Option(
        DEFAULT_APPROVAL_SECRET_PATH,
        help="Path to the local HMAC secret file.",
    ),
) -> None:
    """Evaluate policy locally, run if allowed, and persist a trace record."""
    policy_obj = load_policy(policy)
    store = TraceStore(trace)
    secret: bytes | None = None
    if approval_token:
        try:
            secret = resolve_approval_secret(secret_path=approval_secret)
        except ApprovalError as exc:
            typer.echo(json.dumps({"error": str(exc)}))
            raise typer.Exit(code=1) from exc
    try:
        response = execute_run(
            policy_obj,
            store,
            workspace=str(workspace),
            command=command,
            timeout_seconds=timeout,
            workspace_root=str(workspace_root) if workspace_root else None,
            approval_token=approval_token,
            approval_secret=secret,
        )
    except RunExecutionError as exc:
        typer.echo(json.dumps({"error": exc.detail}))
        raise typer.Exit(code=1) from exc
    payload = response.model_dump(mode="json")
    if response.decision.value == "denied":
        payload["message"] = "denied"
        typer.echo(json.dumps(payload))
        raise typer.Exit(code=1)
    if response.decision.value == "approval_required":
        payload["message"] = "approval_required"
        typer.echo(json.dumps(payload))
        raise typer.Exit(code=2)

    typer.echo(json.dumps(payload))


@app.command()
def explain(
    command: str = typer.Option(..., help="Shell command to evaluate against policy."),
    policy: Path = typer.Option(DEFAULT_POLICY_PATH, help="Path to policy JSON file."),
) -> None:
    """Evaluate a command against policy without executing or writing traces."""
    evaluation = evaluate_policy(load_policy(policy), command)
    typer.echo(json.dumps(evaluation.model_dump(mode="json")))


@app.command()
def replay(
    run_id: str = typer.Option(..., help="Run ID to replay from the trace log."),
    policy: Path = typer.Option(DEFAULT_POLICY_PATH, help="Path to policy JSON file."),
    trace: Path = typer.Option(DEFAULT_TRACE_PATH, help="Path to JSONL trace log."),
    timeout: int = typer.Option(
        DEFAULT_TIMEOUT_SECONDS,
        help="Maximum seconds before the command is terminated.",
    ),
    workspace_root: Path | None = typer.Option(
        None,
        help="Require the stored workspace to resolve inside this directory.",
    ),
    approval_token: str | None = typer.Option(
        None,
        help="HMAC approval token for require_approval commands.",
    ),
    approval_secret: Path = typer.Option(
        DEFAULT_APPROVAL_SECRET_PATH,
        help="Path to the local HMAC secret file.",
    ),
) -> None:
    """Re-run a stored command after re-evaluating current policy."""
    policy_obj = load_policy(policy)
    store = TraceStore(trace)
    secret: bytes | None = None
    if approval_token:
        try:
            secret = resolve_approval_secret(secret_path=approval_secret)
        except ApprovalError as exc:
            typer.echo(json.dumps({"error": str(exc)}))
            raise typer.Exit(code=1) from exc
    try:
        response = replay_run(
            policy_obj,
            store,
            run_id,
            timeout_seconds=timeout,
            workspace_root=str(workspace_root) if workspace_root else None,
            approval_token=approval_token,
            approval_secret=secret,
        )
    except RunExecutionError as exc:
        typer.echo(json.dumps({"error": exc.detail}))
        raise typer.Exit(code=1) from exc
    payload = response.model_dump(mode="json")
    if response.decision.value == "denied":
        payload["message"] = "denied"
        typer.echo(json.dumps(payload))
        raise typer.Exit(code=1)
    if response.decision.value == "approval_required":
        payload["message"] = "approval_required"
        typer.echo(json.dumps(payload))
        raise typer.Exit(code=2)

    typer.echo(json.dumps(payload))


@traces_app.command("list")
def list_traces(
    trace: Path = typer.Option(DEFAULT_TRACE_PATH, help="Path to JSONL trace log."),
    limit: int = typer.Option(20, help="Maximum number of traces to return."),
    decision: str | None = typer.Option(None, help="Filter by decision value."),
) -> None:
    """List recent trace records from the JSONL log."""
    store = TraceStore(trace)
    records = store.list_runs(limit=limit, decision=decision)
    typer.echo(json.dumps([record.model_dump(mode="json") for record in records]))


@traces_app.command("get")
def get_trace(
    run_id: str = typer.Option(..., help="Run ID to fetch."),
    trace: Path = typer.Option(DEFAULT_TRACE_PATH, help="Path to JSONL trace log."),
) -> None:
    """Fetch a single trace record by run ID."""
    store = TraceStore(trace)
    record = store.get(run_id)
    if record is None:
        typer.echo(json.dumps({"error": "Run not found."}))
        raise typer.Exit(code=1)
    typer.echo(json.dumps(record.model_dump(mode="json")))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
