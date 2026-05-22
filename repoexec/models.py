from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PolicyDecision(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    APPROVAL_REQUIRED = "approval_required"


class RunRequest(BaseModel):
    workspace: str
    command: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    run_id: str
    decision: PolicyDecision
    message: str
    exit_code: int | None = None
    duration_ms: int | None = None
    stdout: str | None = None
    stderr: str | None = None


class TraceRecord(BaseModel):
    run_id: str
    timestamp: datetime
    workspace: str
    command: str
    decision: PolicyDecision
    exit_code: int | None = None
    duration_ms: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def new_id(cls) -> str:
        return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
