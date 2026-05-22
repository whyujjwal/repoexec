from repoexec.models import PolicyDecision, TraceRecord, utc_now
from repoexec.trace_view import format_compact_detail, format_compact_list


def test_format_compact_list_shows_table_header_and_rows():
    records = [
        TraceRecord(
            run_id="run-abc-123",
            timestamp=utc_now(),
            workspace=".",
            command="pytest -q",
            decision=PolicyDecision.ALLOWED,
            exit_code=0,
            duration_ms=812,
        )
    ]

    output = format_compact_list(records)

    assert "RUN ID" in output
    assert "pytest -q" in output
    assert "allowed" in output
    assert "812" in output


def test_format_compact_list_empty():
    assert format_compact_list([]) == "No traces found."


def test_format_compact_detail_includes_policy_and_truncates_output():
    record = TraceRecord(
        run_id="run-detail",
        timestamp=utc_now(),
        workspace="/tmp/repo",
        command="echo hello",
        decision=PolicyDecision.DENIED,
        policy_reason="Command matched deny rule 'echo *'.",
        matched_rule="echo *",
        rule_category="deny",
        stdout="x" * 600,
    )

    output = format_compact_detail(record, output_preview=100)

    assert "Run ID:    run-detail" in output
    assert "Policy:    Command matched deny rule" in output
    assert "600 chars total, truncated" in output
