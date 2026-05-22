import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from repoexec.approval import (
    ApprovalError,
    issue_approval_token,
    resolve_approval_secret,
    verify_approval_token,
)


@pytest.fixture
def secret() -> bytes:
    return b"test-secret-key"


def test_issue_and_verify_round_trip(secret: bytes):
    token = issue_approval_token(
        workspace="/tmp/repo",
        command="git push origin main",
        secret=secret,
        ttl_seconds=3600,
    )
    claims = verify_approval_token(
        token=token,
        workspace="/tmp/repo",
        command="git push origin main",
        secret=secret,
    )
    assert claims.workspace == "/tmp/repo"
    assert claims.command == "git push origin main"
    assert claims.exp is not None


def test_verify_rejects_tampered_signature(secret: bytes):
    token = issue_approval_token(
        workspace="/tmp/repo",
        command="git push origin main",
        secret=secret,
        ttl_seconds=3600,
    )
    payload_part, _signature = token.split(".")
    tampered = f"{payload_part}.invalid-signature"

    with pytest.raises(ApprovalError, match="signature"):
        verify_approval_token(
            token=tampered,
            workspace="/tmp/repo",
            command="git push origin main",
            secret=secret,
        )


def test_verify_rejects_workspace_mismatch(secret: bytes):
    token = issue_approval_token(
        workspace="/tmp/repo",
        command="git push origin main",
        secret=secret,
        ttl_seconds=3600,
    )

    with pytest.raises(ApprovalError, match="workspace"):
        verify_approval_token(
            token=token,
            workspace="/other/repo",
            command="git push origin main",
            secret=secret,
        )


def test_verify_rejects_command_mismatch(secret: bytes):
    token = issue_approval_token(
        workspace="/tmp/repo",
        command="git push origin main",
        secret=secret,
        ttl_seconds=3600,
    )

    with pytest.raises(ApprovalError, match="command"):
        verify_approval_token(
            token=token,
            workspace="/tmp/repo",
            command="git push origin other",
            secret=secret,
        )


def test_verify_rejects_expired_token(secret: bytes):
    token = issue_approval_token(
        workspace="/tmp/repo",
        command="git push origin main",
        secret=secret,
        ttl_seconds=60,
    )
    expired_now = datetime(2099, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ApprovalError, match="expired"):
        verify_approval_token(
            token=token,
            workspace="/tmp/repo",
            command="git push origin main",
            secret=secret,
            now=expired_now,
        )


def test_resolve_secret_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("REPOEXEC_APPROVAL_SECRET", "from-env")
    assert resolve_approval_secret() == b"from-env"


def test_resolve_secret_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("REPOEXEC_APPROVAL_SECRET", raising=False)
    secret_path = tmp_path / "approval.secret"
    secret_path.write_bytes(b"from-file")

    assert resolve_approval_secret(secret_path=secret_path) == b"from-file"


def test_resolve_secret_create_if_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("REPOEXEC_APPROVAL_SECRET", raising=False)
    secret_path = tmp_path / ".repoexec" / "approval.secret"

    secret = resolve_approval_secret(secret_path=secret_path, create_if_missing=True)
    assert len(secret) == 32
    assert secret_path.read_bytes() == secret
    assert secret_path.stat().st_mode & 0o777 == 0o600


def test_issue_rejects_empty_command(secret: bytes):
    with pytest.raises(ApprovalError, match="empty command"):
        issue_approval_token(workspace=".", command="   ", secret=secret)
