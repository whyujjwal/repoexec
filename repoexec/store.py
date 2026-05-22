import json
from pathlib import Path

from repoexec.models import TraceRecord


class TraceStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, TraceRecord] = {}
        self._load_index()

    def _load_index(self) -> None:
        if not self.path.exists():
            return

        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = TraceRecord.model_validate_json(line)
            self._index[record.run_id] = record

    def append(self, record: TraceRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json())
            handle.write("\n")
        self._index[record.run_id] = record

    def get(self, run_id: str) -> TraceRecord | None:
        return self._index.get(run_id)

    def list_runs(
        self,
        *,
        limit: int | None = None,
        decision: str | None = None,
        command_contains: str | None = None,
        workspace_contains: str | None = None,
    ) -> list[TraceRecord]:
        records = sorted(
            self._index.values(),
            key=lambda record: record.timestamp,
            reverse=True,
        )
        if decision is not None:
            records = [record for record in records if record.decision.value == decision]
        if command_contains is not None:
            needle = command_contains.casefold()
            records = [
                record for record in records if needle in record.command.casefold()
            ]
        if workspace_contains is not None:
            needle = workspace_contains.casefold()
            records = [
                record for record in records if needle in record.workspace.casefold()
            ]
        if limit is not None:
            records = records[:limit]
        return records
