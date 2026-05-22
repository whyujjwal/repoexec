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
