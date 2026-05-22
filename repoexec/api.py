from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from repoexec.config import DEFAULT_POLICY_PATH, DEFAULT_TRACE_PATH
from repoexec.models import RunRequest, RunResponse, TraceRecord
from repoexec.policy import PolicyEvaluation, evaluate_policy, load_policy
from repoexec.service import RunExecutionError, execute_run_request, replay_run
from repoexec.store import TraceStore


def create_app(
    *,
    policy_path: Path | str = DEFAULT_POLICY_PATH,
    trace_path: Path | str = DEFAULT_TRACE_PATH,
) -> FastAPI:
    app = FastAPI(title="RepoExec", version="0.1.0")
    policy = load_policy(policy_path)
    store = TraceStore(trace_path)

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
    ) -> list[TraceRecord]:
        return store.list_runs(limit=limit, decision=decision)

    @app.post("/runs", response_model=RunResponse)
    def create_run(request: RunRequest) -> RunResponse:
        try:
            return execute_run_request(policy, store, request)
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
    ) -> RunResponse:
        try:
            return replay_run(policy, store, run_id, timeout_seconds=timeout_seconds)
        except RunExecutionError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return app
