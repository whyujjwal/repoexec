import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from repoexec.config import DEFAULT_TIMEOUT_SECONDS

_BLOCKED_ENV_KEYS = frozenset({"LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "PYTHONPATH"})
_BLOCKED_ENV_PREFIXES = ("LD_", "DYLD_")


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class WorkspaceValidationError(ValueError):
    pass


def _resolve_root(root: Path | str) -> Path:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise WorkspaceValidationError(f"Workspace root does not exist: {root_path}")
    if not root_path.is_dir():
        raise WorkspaceValidationError(f"Workspace root is not a directory: {root_path}")
    return root_path


def validate_workspace(
    workspace: Path | str,
    *,
    allowed_root: Path | str | None = None,
) -> Path:
    workspace_path = Path(workspace).expanduser().resolve()
    if not workspace_path.exists():
        raise WorkspaceValidationError(f"Workspace does not exist: {workspace_path}")
    if not workspace_path.is_dir():
        raise WorkspaceValidationError(f"Workspace is not a directory: {workspace_path}")

    if allowed_root is not None:
        root_path = _resolve_root(allowed_root)
        if not workspace_path.is_relative_to(root_path):
            raise WorkspaceValidationError(
                f"Workspace {workspace_path} is outside allowed root {root_path}"
            )

    return workspace_path


def _restricted_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        if key in _BLOCKED_ENV_KEYS:
            continue
        if key.startswith(_BLOCKED_ENV_PREFIXES):
            continue
        if key in ("BASH_ENV", "ENV"):
            continue
        env[key] = value
    return env


def run_command(
    workspace: Path | str,
    command: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    allowed_root: Path | str | None = None,
) -> CommandResult:
    if not command.strip():
        raise ValueError("Command must not be empty.")

    workspace_path = validate_workspace(workspace, allowed_root=allowed_root)

    start = time.perf_counter()
    completed = subprocess.run(
        ["/bin/sh", "-c", command],
        shell=False,
        cwd=workspace_path,
        env=_restricted_env(),
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
