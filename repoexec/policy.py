import fnmatch
import json
from pathlib import Path

from pydantic import BaseModel, Field

from repoexec.models import PolicyDecision


class Policy(BaseModel):
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    require_approval: list[str] = Field(default_factory=list)


def load_policy(path: Path | str) -> Policy:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Policy.model_validate(data)


def _matches(command: str, pattern: str) -> bool:
    if "*" in pattern or "?" in pattern or "[" in pattern:
        return fnmatch.fnmatch(command, pattern)
    return pattern in command


def evaluate_policy(policy: Policy, command: str) -> PolicyDecision:
    for pattern in policy.deny:
        if _matches(command, pattern):
            return PolicyDecision.DENIED

    for pattern in policy.require_approval:
        if _matches(command, pattern):
            return PolicyDecision.APPROVAL_REQUIRED

    for pattern in policy.allow:
        if _matches(command, pattern):
            return PolicyDecision.ALLOWED

    return PolicyDecision.DENIED
