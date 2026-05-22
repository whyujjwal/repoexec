import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from repoexec.config import DEFAULT_TIMEOUT_SECONDS


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class WorkspaceValidationError(ValueError):
    pass


def validate_workspace(workspace: Path | str) -> Path:
    workspace_path = Path(workspace).expanduser().resolve()
    if not workspace_path.exists():
        raise WorkspaceValidationError(f"Workspace does not exist: {workspace_path}")
    if not workspace_path.is_dir():
        raise WorkspaceValidationError(f"Workspace is not a directory: {workspace_path}")
    return workspace_path


def run_command(
    workspace: Path | str,
    command: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> CommandResult:
    if not command.strip():
        raise ValueError("Command must not be empty.")

    workspace_path = validate_workspace(workspace)

    start = time.perf_counter()
    completed = subprocess.run(
        command,
        shell=True,
        cwd=workspace_path,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    duration_ms = int((time.perf_counter() - start) * 1000)

    return CommandResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_ms=duration_ms,
    )
