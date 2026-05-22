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


def test_validate_workspace_allows_subdirectory(tmp_path: Path):
    root = tmp_path / "root"
    workspace = root / "nested"
    workspace.mkdir(parents=True)
    resolved = validate_workspace(workspace, allowed_root=root)
    assert resolved == workspace.resolve()


def test_validate_workspace_rejects_path_outside_root(tmp_path: Path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    with pytest.raises(WorkspaceValidationError, match="outside allowed root"):
        validate_workspace(outside, allowed_root=root)


def test_validate_workspace_rejects_parent_traversal(tmp_path: Path):
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    with pytest.raises(WorkspaceValidationError, match="outside allowed root"):
        validate_workspace(nested / "..", allowed_root=root / "nested")


def test_validate_workspace_rejects_missing_root(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    missing_root = tmp_path / "missing-root"
    with pytest.raises(WorkspaceValidationError, match="Workspace root does not exist"):
        validate_workspace(workspace, allowed_root=missing_root)


def test_run_command_rejects_empty_command(tmp_path: Path):
    with pytest.raises(ValueError, match="empty"):
        run_command(tmp_path, "   ")
