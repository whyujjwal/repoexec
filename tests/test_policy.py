from repoexec.models import PolicyDecision
from repoexec.policy import Policy, evaluate_policy


def test_allow_matches_command():
    policy = Policy(allow=["echo *"])
    evaluation = evaluate_policy(policy, "echo hello")
    assert evaluation.decision is PolicyDecision.ALLOWED
    assert evaluation.matched_rule == "echo *"
    assert evaluation.rule_category == "allow"


def test_deny_wins_over_allow():
    policy = Policy(allow=["*"], deny=["rm *"])
    evaluation = evaluate_policy(policy, "rm -rf /")
    assert evaluation.decision is PolicyDecision.DENIED
    assert evaluation.matched_rule == "rm *"
    assert evaluation.rule_category == "deny"


def test_approval_wins_over_allow():
    policy = Policy(allow=["*"], require_approval=["git push*"])
    evaluation = evaluate_policy(policy, "git push origin main")
    assert evaluation.decision is PolicyDecision.APPROVAL_REQUIRED
    assert evaluation.matched_rule == "git push*"


def test_deny_wins_over_approval():
    policy = Policy(
        allow=["*"],
        deny=["sudo*"],
        require_approval=["sudo apt*"],
    )
    evaluation = evaluate_policy(policy, "sudo apt install foo")
    assert evaluation.decision is PolicyDecision.DENIED
    assert evaluation.rule_category == "deny"


def test_unlisted_command_is_denied():
    policy = Policy(allow=["echo *"])
    evaluation = evaluate_policy(policy, "wget http://example.com")
    assert evaluation.decision is PolicyDecision.DENIED
    assert evaluation.rule_category == "default"
    assert "did not match" in evaluation.reason


def test_substring_matching_without_glob():
    policy = Policy(allow=["git status"])
    evaluation = evaluate_policy(policy, "git status --short")
    assert evaluation.decision is PolicyDecision.ALLOWED
