# RepoExec

RepoExec is an open-source, GitHub-native execution layer for coding agents. It runs approved shell commands inside a repository workspace, evaluates them against a local policy file, and persists structured run traces to disk.

## Why RepoExec

Coding agents need a reliable place to run commands with guardrails. RepoExec is the first slice of that infrastructure:

- **Policy checks** — allow, deny, or require approval for commands
- **Run traces** — every request is logged as JSONL for audit and replay
- **Simple interfaces** — HTTP API for integrations and a CLI for local debugging

## Quickstart

```bash
python3 -m pip install -e '.[dev]'
pytest -q
```

Run a command locally:

```bash
python3 -m repoexec.cli run --workspace . --command 'echo hello' --policy examples/policy.json
```

Start the HTTP server:

```bash
python3 -m repoexec.cli serve --policy examples/policy.json
```

## Policy file

Policies are JSON files with three rule lists:

```json
{
  "allow": ["echo *", "pytest*"],
  "deny": ["rm *", "sudo*"],
  "require_approval": ["git push*"]
}
```

Precedence:

1. **deny** wins over everything
2. **require_approval** wins over allow
3. **allow** permits execution
4. Unmatched commands are denied

Matching supports simple substrings and glob patterns (`*`, `?`).

## HTTP API

### `GET /healthz`

Health check.

### `POST /runs`

Submit an execution request:

```bash
curl -s -X POST http://127.0.0.1:8765/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "workspace": ".",
    "command": "echo hello",
    "metadata": {"agent": "demo"}
  }'
```

Example response:

```json
{
  "run_id": "…",
  "decision": "allowed",
  "message": "Command executed.",
  "exit_code": 0,
  "duration_ms": 12,
  "stdout": "hello\n",
  "stderr": ""
}
```

Denied and approval-required commands return structured responses without executing.

### `GET /runs/{run_id}`

Fetch a persisted trace record by ID.

## Trace log

Traces append to `.repoexec/traces.jsonl` by default. Each line is a JSON object with:

- `run_id`, `timestamp`, `workspace`, `command`
- `decision` (`allowed`, `denied`, `approval_required`)
- `exit_code`, `duration_ms`, `stdout`, `stderr` (when executed)
- `metadata`

## CLI

```bash
repoexec serve [--host 127.0.0.1] [--port 8765] [--policy examples/policy.json]
repoexec run --workspace . --command 'echo hello' --policy examples/policy.json
```

## Development

```bash
python3 -m pip install -e '.[dev]'
pytest -q
```

## License

MIT (placeholder — add a LICENSE file before publishing).
