import base64
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from repoexec.config import DEFAULT_APPROVAL_SECRET_PATH

_TOKEN_VERSION = 1
_DEFAULT_TTL_SECONDS = 3600


class ApprovalError(Exception):
    """Raised when an approval token cannot be issued or verified."""


@dataclass(frozen=True)
class ApprovalClaims:
    workspace: str
    command: str
    exp: int | None


def resolve_approval_secret(
    *,
    secret_path: Path | str | None = None,
    create_if_missing: bool = False,
) -> bytes:
    env_secret = os.environ.get("REPOEXEC_APPROVAL_SECRET")
    if env_secret:
        return env_secret.encode("utf-8")

    path = Path(secret_path) if secret_path is not None else DEFAULT_APPROVAL_SECRET_PATH
    if path.exists():
        secret = path.read_bytes().strip()
        if not secret:
            raise ApprovalError(f"Approval secret file is empty: {path}")
        return secret

    if create_if_missing:
        path.parent.mkdir(parents=True, exist_ok=True)
        secret = secrets.token_bytes(32)
        path.write_bytes(secret)
        path.chmod(0o600)
        return secret

    raise ApprovalError(
        "No approval secret configured. Set REPOEXEC_APPROVAL_SECRET or create "
        f"{path}, or pass --create-secret when issuing a token."
    )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _canonical_payload(claims: ApprovalClaims) -> dict[str, object]:
    payload: dict[str, object] = {
        "v": _TOKEN_VERSION,
        "workspace": claims.workspace,
        "command": claims.command,
    }
    if claims.exp is not None:
        payload["exp"] = claims.exp
    return payload


def _sign_payload(payload: dict[str, object], secret: bytes) -> str:
    payload_bytes = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hmac.new(secret, payload_bytes, hashlib.sha256).digest()
    return _b64url_encode(digest)


def issue_approval_token(
    *,
    workspace: str,
    command: str,
    secret: bytes,
    ttl_seconds: int | None = _DEFAULT_TTL_SECONDS,
) -> str:
    if not command.strip():
        raise ApprovalError("Cannot issue approval token for an empty command.")

    exp: int | None = None
    if ttl_seconds is not None:
        if ttl_seconds <= 0:
            raise ApprovalError("Token TTL must be positive.")
        exp = int(datetime.now(timezone.utc).timestamp()) + ttl_seconds

    claims = ApprovalClaims(workspace=workspace, command=command, exp=exp)
    payload = _canonical_payload(claims)
    payload_part = _b64url_encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signature_part = _sign_payload(payload, secret)
    return f"{payload_part}.{signature_part}"


def verify_approval_token(
    *,
    token: str,
    workspace: str,
    command: str,
    secret: bytes,
    now: datetime | None = None,
) -> ApprovalClaims:
    if not token.strip():
        raise ApprovalError("Approval token is missing.")

    parts = token.split(".")
    if len(parts) != 2:
        raise ApprovalError("Approval token has invalid format.")

    payload_part, signature_part = parts
    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise ApprovalError("Approval token payload is invalid.") from exc

    if payload.get("v") != _TOKEN_VERSION:
        raise ApprovalError("Approval token version is unsupported.")

    expected_signature = _sign_payload(payload, secret)
    if not hmac.compare_digest(signature_part, expected_signature):
        raise ApprovalError("Approval token signature is invalid.")

    token_workspace = payload.get("workspace")
    token_command = payload.get("command")
    if not isinstance(token_workspace, str) or not isinstance(token_command, str):
        raise ApprovalError("Approval token payload is missing workspace or command.")

    if token_workspace != workspace:
        raise ApprovalError("Approval token workspace does not match the request.")
    if token_command != command:
        raise ApprovalError("Approval token command does not match the request.")

    exp = payload.get("exp")
    if exp is not None:
        if not isinstance(exp, int):
            raise ApprovalError("Approval token expiry is invalid.")
        current = now or datetime.now(timezone.utc)
        if int(current.timestamp()) > exp:
            raise ApprovalError("Approval token has expired.")

    return ApprovalClaims(workspace=token_workspace, command=token_command, exp=exp)
