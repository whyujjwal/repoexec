from repoexec.models import TraceRecord

DEFAULT_OUTPUT_PREVIEW = 500


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[: limit - 3] + "...", True


def format_compact_list(records: list[TraceRecord]) -> str:
    if not records:
        return "No traces found."

    lines = [
        f"{'RUN ID':<36} {'TIME':<20} {'DECISION':<18} {'EXIT':>4} {'MS':>6}  COMMAND",
        "-" * 100,
    ]
    for record in records:
        run_id = record.run_id[:36]
        timestamp = record.timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        exit_code = "" if record.exit_code is None else str(record.exit_code)
        duration_ms = "" if record.duration_ms is None else str(record.duration_ms)
        command = record.command.replace("\n", " ")
        command, _ = _truncate(command, 60)
        lines.append(
            f"{run_id:<36} {timestamp:<20} {record.decision.value:<18} "
            f"{exit_code:>4} {duration_ms:>6}  {command}"
        )
    return "\n".join(lines)


def format_compact_detail(
    record: TraceRecord,
    *,
    output_preview: int = DEFAULT_OUTPUT_PREVIEW,
) -> str:
    lines = [
        f"Run ID:    {record.run_id}",
        f"Time:      {record.timestamp.isoformat()}",
        f"Workspace: {record.workspace}",
        f"Command:   {record.command}",
        f"Decision:  {record.decision.value}",
    ]
    if record.policy_reason:
        lines.append(f"Policy:    {record.policy_reason}")
    if record.matched_rule:
        lines.append(f"Rule:      {record.matched_rule} ({record.rule_category})")
    if record.exit_code is not None:
        lines.append(f"Exit:      {record.exit_code}")
    if record.duration_ms is not None:
        lines.append(f"Duration:  {record.duration_ms} ms")

    lines.extend(_format_stream("Stdout", record.stdout, output_preview))
    lines.extend(_format_stream("Stderr", record.stderr, output_preview))

    if record.metadata:
        lines.append(f"Metadata:  {record.metadata}")

    return "\n".join(lines)


def _format_stream(label: str, text: str | None, limit: int) -> list[str]:
    if text is None:
        return []
    if not text:
        return [f"{label}:     (empty)"]

    preview, truncated = _truncate(text, limit)
    lines = [f"{label}:"]
    for line in preview.splitlines() or [preview]:
        lines.append(f"  {line}")
    if truncated:
        lines.append(f"  ... ({len(text)} chars total, truncated)")
    return lines
