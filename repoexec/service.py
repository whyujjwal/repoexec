import subprocess
from typing import Any

from repoexec.approval import ApprovalError, verify_approval_token
from repoexec.config import DEFAULT_TIMEOUT_SECONDS
from repoexec.models import PolicyDecision, RunRequest, RunResponse, TraceRecord, utc_now
from repoexec.policy import Policy, evaluate_policy
from repoexec.runner import WorkspaceValidationError, run_command, validate_workspace
from repoexec.store import TraceStore


class RunExecutionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def execute_run(
    policy: Policy,
    store: TraceStore,
    *,
    workspace: str,
    command: str,
    metadata: dict[str, Any] | None = None,
    timeout_seconds: int | None = None,
    replay_of: str | None = None,
    workspace_root: str | None = None,
    approval_token: str | None = None,
    approval_secret: bytes | None = None,
) -> RunResponse:
    if not command.strip():
        raise RunExecutionError(400, "Command must not be empty.")

    try:
        validate_workspace(workspace, allowed_root=workspace_root)
    except WorkspaceValidationError as exc:
        raise RunExecutionError(400, str(exc)) from exc

    run_metadata = dict(metadata or {})
    if replay_of is not None:
        run_metadata["replayed_from"] = replay_of

    run_id = TraceRecord.new_id()
    evaluation = evaluate_policy(policy, command)
    decision = evaluation.decision
    policy_reason = evaluation.reason
    matched_rule = evaluation.matched_rule
    rule_category = evaluation.rule_category
    effective_timeout = timeout_seconds or DEFAULT_TIMEOUT_SECONDS

    if decision is PolicyDecision.DENIED:
        record = TraceRecord(
            run_id=run_id,
            timestamp=utc_now(),
            workspace=workspace,
            command=command,
            decision=decision,
            policy_reason=evaluation.reason,
            matched_rule=evaluation.matched_rule,
            rule_category=evaluation.rule_category,
            metadata=run_metadata,
        )
        store.append(record)
        return RunResponse(
            run_id=run_id,
            decision=decision,
            message="Command denied by policy.",
            policy_reason=policy_reason,
            matched_rule=matched_rule,
            rule_category=rule_category,
        )

    if decision is PolicyDecision.APPROVAL_REQUIRED:
        approved = False
        if approval_token and approval_secret:
            try:
                verify_approval_token(
                    token=approval_token,
                    workspace=workspace,
                    command=command,
                    secret=approval_secret,
                )
                approved = True
            except ApprovalError:
                approved = False

        if not approved:
            record = TraceRecord(
                run_id=run_id,
                timestamp=utc_now(),
                workspace=workspace,
                command=command,
                decision=decision,
                policy_reason=policy_reason,
                matched_rule=matched_rule,
                rule_category=rule_category,
                metadata=run_metadata,
            )
            store.append(record)
            return RunResponse(
                run_id=run_id,
                decision=decision,
                message="Command requires approval before execution.",
                policy_reason=policy_reason,
                matched_rule=matched_rule,
                rule_category=rule_category,
            )

        run_metadata["approved_via_token"] = True
        decision = PolicyDecision.ALLOWED
        policy_reason = (
            f"Command approved via token after matching require_approval rule "
            f"'{evaluation.matched_rule}'."
        )
        matched_rule = evaluation.matched_rule
        rule_category = evaluation.rule_category

    try:
        result = run_command(
            workspace,
            command,
            timeout_seconds=effective_timeout,
            allowed_root=workspace_root,
        )
    except ValueError as exc:
        raise RunExecutionError(400, str(exc)) from exc
    except WorkspaceValidationError as exc:
        raise RunExecutionError(400, str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raise RunExecutionError(408, "Command timed out.") from exc

    record = TraceRecord(
        run_id=run_id,
        timestamp=utc_now(),
        workspace=workspace,
        command=command,
        decision=decision,
        policy_reason=policy_reason,
        matched_rule=matched_rule,
        rule_category=rule_category,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        stdout=result.stdout,
        stderr=result.stderr,
        metadata=run_metadata,
    )
    store.append(record)
    return RunResponse(
        run_id=run_id,
        decision=decision,
        message="Command executed.",
        policy_reason=policy_reason,
        matched_rule=matched_rule,
        rule_category=rule_category,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def execute_run_request(
    policy: Policy,
    store: TraceStore,
    request: RunRequest,
    *,
    workspace_root: str | None = None,
    approval_secret: bytes | None = None,
) -> RunResponse:
    return execute_run(
        policy,
        store,
        workspace=request.workspace,
        command=request.command,
        metadata=request.metadata,
        timeout_seconds=request.timeout_seconds,
        workspace_root=workspace_root,
        approval_token=request.approval_token,
        approval_secret=approval_secret,
    )


def replay_run(
    policy: Policy,
    store: TraceStore,
    run_id: str,
    *,
    timeout_seconds: int | None = None,
    workspace_root: str | None = None,
    approval_token: str | None = None,
    approval_secret: bytes | None = None,
) -> RunResponse:
    original = store.get(run_id)
    if original is None:
        raise RunExecutionError(404, "Run not found.")

    return execute_run(
        policy,
        store,
        workspace=original.workspace,
        command=original.command,
        metadata=original.metadata,
        timeout_seconds=timeout_seconds,
        replay_of=run_id,
        workspace_root=workspace_root,
        approval_token=approval_token,
        approval_secret=approval_secret,
    )
