import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException

from repoexec.config import DEFAULT_POLICY_PATH, DEFAULT_TRACE_PATH
from repoexec.models import (
    PolicyDecision,
    RunRequest,
    RunResponse,
    TraceRecord,
    utc_now,
)
from repoexec.policy import evaluate_policy, load_policy
from repoexec.runner import run_command
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

    @app.post("/runs", response_model=RunResponse)
    def create_run(request: RunRequest) -> RunResponse:
        run_id = TraceRecord.new_id()
        decision = evaluate_policy(policy, request.command)

        if decision is PolicyDecision.DENIED:
            record = TraceRecord(
                run_id=run_id,
                timestamp=utc_now(),
                workspace=request.workspace,
                command=request.command,
                decision=decision,
                metadata=request.metadata,
            )
            store.append(record)
            return RunResponse(
                run_id=run_id,
                decision=decision,
                message="Command denied by policy.",
            )

        if decision is PolicyDecision.APPROVAL_REQUIRED:
            record = TraceRecord(
                run_id=run_id,
                timestamp=utc_now(),
                workspace=request.workspace,
                command=request.command,
                decision=decision,
                metadata=request.metadata,
            )
            store.append(record)
            return RunResponse(
                run_id=run_id,
                decision=decision,
                message="Command requires approval before execution.",
            )

        try:
            result = run_command(request.workspace, request.command)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=408, detail="Command timed out.") from exc

        record = TraceRecord(
            run_id=run_id,
            timestamp=utc_now(),
            workspace=request.workspace,
            command=request.command,
            decision=decision,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            stdout=result.stdout,
            stderr=result.stderr,
            metadata=request.metadata,
        )
        store.append(record)
        return RunResponse(
            run_id=run_id,
            decision=decision,
            message="Command executed.",
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    @app.get("/runs/{run_id}", response_model=TraceRecord)
    def get_run(run_id: str) -> TraceRecord:
        record = store.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        return record

    return app
