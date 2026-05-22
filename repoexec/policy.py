import fnmatch
import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

from repoexec.models import PolicyDecision

_SEGMENT_SPLIT = re.compile(r"\s*(?:;|&&|\|\||\|)\s*")


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


def split_command_segments(command: str) -> list[str]:
    parts = _SEGMENT_SPLIT.split(command.strip())
    return [part.strip() for part in parts if part.strip()]


def _evaluate_single_command(policy: Policy, command: str) -> PolicyEvaluation:
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


def _combine_segment_evaluations(
    segments: list[str],
    evaluations: list[PolicyEvaluation],
) -> PolicyEvaluation:
    for segment, evaluation in zip(segments, evaluations):
        if evaluation.decision is PolicyDecision.DENIED:
            return PolicyEvaluation(
                decision=PolicyDecision.DENIED,
                reason=f"Compound command blocked: segment '{segment}' — {evaluation.reason}",
                matched_rule=evaluation.matched_rule,
                rule_category=evaluation.rule_category,
            )

    for segment, evaluation in zip(segments, evaluations):
        if evaluation.decision is PolicyDecision.APPROVAL_REQUIRED:
            return PolicyEvaluation(
                decision=PolicyDecision.APPROVAL_REQUIRED,
                reason=(
                    f"Compound command requires approval: segment '{segment}' — "
                    f"{evaluation.reason}"
                ),
                matched_rule=evaluation.matched_rule,
                rule_category=evaluation.rule_category,
            )

    return PolicyEvaluation(
        decision=PolicyDecision.ALLOWED,
        reason=f"All {len(segments)} command segments matched allow rules.",
        matched_rule=evaluations[-1].matched_rule,
        rule_category="allow",
    )


def evaluate_policy(policy: Policy, command: str) -> PolicyEvaluation:
    segments = split_command_segments(command)
    if len(segments) <= 1:
        return _evaluate_single_command(policy, command)

    evaluations = [_evaluate_single_command(policy, segment) for segment in segments]
    return _combine_segment_evaluations(segments, evaluations)
