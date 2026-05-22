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


def run_command(
    workspace: Path | str,
    command: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> CommandResult:
    workspace_path = Path(workspace).resolve()
    if not workspace_path.is_dir():
        raise ValueError(f"Workspace does not exist or is not a directory: {workspace_path}")

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
