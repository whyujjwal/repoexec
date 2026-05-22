import fnmatch
import json
from pathlib import Path

from pydantic import BaseModel, Field

from repoexec.models import PolicyDecision


class Policy(BaseModel):
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    require_approval: list[str] = Field(default_factory=list)


class PolicyEvaluation(BaseModel):
    decision: PolicyDecision
    reason: str
    matched_rule: str | None = None
    rule_category: str | None = None


def load_policy(path: Path | str) -> Policy:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Policy.model_validate(data)


def _matches(command: str, pattern: str) -> bool:
    if "*" in pattern or "?" in pattern or "[" in pattern:
        return fnmatch.fnmatch(command, pattern)
    return pattern in command


def evaluate_policy(policy: Policy, command: str) -> PolicyEvaluation:
    for pattern in policy.deny:
        if _matches(command, pattern):
            return PolicyEvaluation(
                decision=PolicyDecision.DENIED,
                reason=f"Command matched deny rule '{pattern}'.",
                matched_rule=pattern,
                rule_category="deny",
            )

    for pattern in policy.require_approval:
        if _matches(command, pattern):
            return PolicyEvaluation(
                decision=PolicyDecision.APPROVAL_REQUIRED,
                reason=f"Command matched require_approval rule '{pattern}'.",
                matched_rule=pattern,
                rule_category="require_approval",
            )

    for pattern in policy.allow:
        if _matches(command, pattern):
            return PolicyEvaluation(
                decision=PolicyDecision.ALLOWED,
                reason=f"Command matched allow rule '{pattern}'.",
                matched_rule=pattern,
                rule_category="allow",
            )

    return PolicyEvaluation(
        decision=PolicyDecision.DENIED,
        reason="Command did not match any allow rule.",
        rule_category="default",
    )
