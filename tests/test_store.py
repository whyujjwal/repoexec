from pathlib import Path

from repoexec.models import PolicyDecision, TraceRecord, utc_now
from repoexec.store import TraceStore


def test_append_and_get_trace(tmp_path: Path):
    trace_path = tmp_path / "traces.jsonl"
    store = TraceStore(trace_path)

    record = TraceRecord(
        run_id="run-1",
        timestamp=utc_now(),
        workspace="/tmp/workspace",
        command="echo hello",
        decision=PolicyDecision.ALLOWED,
        exit_code=0,
        duration_ms=12,
        stdout="hello\n",
        stderr="",
        metadata={"source": "test"},
    )
    store.append(record)

    loaded = store.get("run-1")
    assert loaded is not None
    assert loaded.command == "echo hello"
    assert loaded.stdout == "hello\n"


def test_reload_index_from_disk(tmp_path: Path):
    trace_path = tmp_path / "traces.jsonl"
    store = TraceStore(trace_path)
    store.append(
        TraceRecord(
            run_id="run-2",
            timestamp=utc_now(),
            workspace=".",
            command="ls",
            decision=PolicyDecision.DENIED,
        )
    )

    reloaded = TraceStore(trace_path)
    assert reloaded.get("run-2") is not None
    assert reloaded.get("run-2").decision is PolicyDecision.DENIED


def test_list_runs_returns_newest_first(tmp_path: Path):
    trace_path = tmp_path / "traces.jsonl"
    store = TraceStore(trace_path)

    first = TraceRecord(
        run_id="run-old",
        timestamp=utc_now(),
        workspace=".",
        command="echo one",
        decision=PolicyDecision.ALLOWED,
    )
    second = TraceRecord(
        run_id="run-new",
        timestamp=utc_now(),
        workspace=".",
        command="echo two",
        decision=PolicyDecision.DENIED,
    )
    store.append(first)
    store.append(second)

    listed = store.list_runs(limit=10)
    assert [record.run_id for record in listed] == ["run-new", "run-old"]


def test_list_runs_filters_by_decision(tmp_path: Path):
    trace_path = tmp_path / "traces.jsonl"
    store = TraceStore(trace_path)
    store.append(
        TraceRecord(
            run_id="run-allowed",
            timestamp=utc_now(),
            workspace=".",
            command="echo ok",
            decision=PolicyDecision.ALLOWED,
        )
    )
    store.append(
        TraceRecord(
            run_id="run-denied",
            timestamp=utc_now(),
            workspace=".",
            command="rm -rf /",
            decision=PolicyDecision.DENIED,
        )
    )

    denied = store.list_runs(decision="denied")
    assert len(denied) == 1
    assert denied[0].run_id == "run-denied"
