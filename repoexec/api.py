from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from repoexec.approval import ApprovalError, resolve_approval_secret
from repoexec.config import DEFAULT_APPROVAL_SECRET_PATH, DEFAULT_POLICY_PATH, DEFAULT_TRACE_PATH
from repoexec.models import RunRequest, RunResponse, TraceRecord
from repoexec.policy import PolicyEvaluation, evaluate_policy, load_policy
from repoexec.service import RunExecutionError, execute_run_request, replay_run
from repoexec.store import TraceStore


def create_app(
    *,
    policy_path: Path | str = DEFAULT_POLICY_PATH,
    trace_path: Path | str = DEFAULT_TRACE_PATH,
    workspace_root: Path | str | None = None,
    approval_secret_path: Path | str | None = DEFAULT_APPROVAL_SECRET_PATH,
) -> FastAPI:
    app = FastAPI(title="RepoExec", version="0.1.0")
    policy = load_policy(policy_path)
    store = TraceStore(trace_path)
    resolved_workspace_root = str(Path(workspace_root).resolve()) if workspace_root else None
    approval_secret: bytes | None = None
    try:
        approval_secret = resolve_approval_secret(secret_path=approval_secret_path)
    except ApprovalError:
        approval_secret = None

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/explain", response_model=PolicyEvaluation)
    def explain_command(command: str = Query(..., min_length=1)) -> PolicyEvaluation:
        return evaluate_policy(policy, command)

    @app.get("/runs", response_model=list[TraceRecord])
    def list_runs(
        limit: int | None = Query(default=50, ge=1, le=500),
        decision: str | None = Query(default=None),
        command: str | None = Query(default=None, min_length=1),
        workspace: str | None = Query(default=None, min_length=1),
    ) -> list[TraceRecord]:
        return store.list_runs(
            limit=limit,
            decision=decision,
            command_contains=command,
            workspace_contains=workspace,
        )

    @app.post("/runs", response_model=RunResponse)
    def create_run(request: RunRequest) -> RunResponse:
        try:
            return execute_run_request(
                policy,
                store,
                request,
                workspace_root=resolved_workspace_root,
                approval_secret=approval_secret,
            )
        except RunExecutionError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    @app.get("/runs/{run_id}", response_model=TraceRecord)
    def get_run(run_id: str) -> TraceRecord:
        record = store.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        return record

    @app.post("/runs/{run_id}/replay", response_model=RunResponse)
    def replay_run_endpoint(
        run_id: str,
        timeout_seconds: int | None = Query(default=None, ge=1),
        approval_token: str | None = Query(default=None),
    ) -> RunResponse:
        try:
            return replay_run(
                policy,
                store,
                run_id,
                timeout_seconds=timeout_seconds,
                workspace_root=resolved_workspace_root,
                approval_token=approval_token,
                approval_secret=approval_secret,
            )
        except RunExecutionError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return app
