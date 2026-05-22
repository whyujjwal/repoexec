from pathlib import Path

import pytest

from repoexec.runner import WorkspaceValidationError, run_command, validate_workspace


def test_validate_workspace_resolves_existing_directory(tmp_path: Path):
    workspace = validate_workspace(tmp_path)
    assert workspace == tmp_path.resolve()


def test_validate_workspace_rejects_missing_path(tmp_path: Path):
    missing = tmp_path / "missing"
    with pytest.raises(WorkspaceValidationError, match="does not exist"):
        validate_workspace(missing)


def test_validate_workspace_rejects_file_path(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(WorkspaceValidationError, match="not a directory"):
        validate_workspace(file_path)


def test_run_command_rejects_empty_command(tmp_path: Path):
    with pytest.raises(ValueError, match="empty"):
        run_command(tmp_path, "   ")
