from repoexec.models import PolicyDecision
from repoexec.policy import Policy, evaluate_policy


def test_allow_matches_command():
    policy = Policy(allow=["echo *"])
    assert evaluate_policy(policy, "echo hello") is PolicyDecision.ALLOWED


def test_deny_wins_over_allow():
    policy = Policy(allow=["*"], deny=["rm *"])
    assert evaluate_policy(policy, "rm -rf /") is PolicyDecision.DENIED


def test_approval_wins_over_allow():
    policy = Policy(allow=["*"], require_approval=["git push*"])
    assert evaluate_policy(policy, "git push origin main") is PolicyDecision.APPROVAL_REQUIRED


def test_deny_wins_over_approval():
    policy = Policy(
        allow=["*"],
        deny=["sudo*"],
        require_approval=["sudo apt*"],
    )
    assert evaluate_policy(policy, "sudo apt install foo") is PolicyDecision.DENIED


def test_unlisted_command_is_denied():
    policy = Policy(allow=["echo *"])
    assert evaluate_policy(policy, "wget http://example.com") is PolicyDecision.DENIED


def test_substring_matching_without_glob():
    policy = Policy(allow=["git status"])
    assert evaluate_policy(policy, "git status --short") is PolicyDecision.ALLOWED
