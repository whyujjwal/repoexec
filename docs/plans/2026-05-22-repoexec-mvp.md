# RepoExec MVP Implementation Plan

> **For Cursor/Hermes:** Build this plan as a narrow, technically strong MVP for a public GitHub repo.

**Goal:** Build an open-source, GitHub-native execution layer for coding agents that can safely run approved shell tasks inside a repository, record traces, and expose a simple HTTP API plus CLI.

**Architecture:** RepoExec is a small Python service + CLI. A FastAPI app accepts execution requests for a workspace, validates them against a local policy file, runs commands through a controlled runner, and stores a structured run trace on disk. A Typer CLI starts the server and supports direct local runs for debugging.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, Typer, Pydantic, pytest.

---

## Product idea
RepoExec is the first slice of a bigger idea: **reliable execution infrastructure for coding agents**.

### Why this project is interesting
- highly relevant to coding agents, MCP-style tools, and repo automation
- useful as OSS and as a long-term company wedge
- strong for developer brand / GitHub presence
- can grow later into approvals, traces, replays, GitHub integration, and browser execution

## MVP scope
### Required capabilities
1. Define a policy file for what commands are allowed, denied, or require approval.
2. Accept an execution request with:
   - workspace path
   - command
   - optional metadata
3. Evaluate policy.
4. If allowed, run the command and capture:
   - exit code
   - stdout
   - stderr
   - timing
5. If approval-required, return a structured blocked response.
6. Persist each run to a local JSONL trace log.
7. Expose this through:
   - a FastAPI API
   - a Typer CLI
8. Include tests for policy evaluation, trace writing, and API behavior.

### Explicitly out of scope for MVP
- auth
- multi-user support
- remote workers
- GitHub webhooks
- browser automation
- database
- queueing

## Suggested file layout
- `pyproject.toml`
- `README.md`
- `repoexec/__init__.py`
- `repoexec/config.py`
- `repoexec/models.py`
- `repoexec/policy.py`
- `repoexec/runner.py`
- `repoexec/store.py`
- `repoexec/api.py`
- `repoexec/cli.py`
- `examples/policy.json`
- `tests/test_policy.py`
- `tests/test_store.py`
- `tests/test_api.py`

## Behavior details
### Policy format
Use a simple JSON file with keys like:
- `allow`
- `deny`
- `require_approval`

Pattern matching can be deliberately simple in MVP:
- substring or glob-style command matching is fine
- deny rules should win over allow rules
- approval rules should win over allow rules unless explicitly denied

### Trace format
Each run should write a JSON object line containing:
- run_id
- timestamp
- workspace
- command
- decision (`allowed`, `denied`, `approval_required`)
- exit_code (if executed)
- duration_ms
- stdout
- stderr
- metadata

### API design
Provide at least:
- `GET /healthz`
- `POST /runs`
- `GET /runs/{run_id}`

Use a local in-memory index for current process reads if helpful, but the source of truth should be the JSONL log file.

### CLI design
Provide at least:
- `repoexec serve`
- `repoexec run --workspace <path> --command <cmd> --policy <file>`

## Implementation priorities
### Task 1: project scaffold
- add `pyproject.toml`
- add package layout
- add README with concept, quickstart, and example API request

### Task 2: core models
- add request/response/trace models with Pydantic

### Task 3: policy engine
- implement policy loading and decision evaluation
- tests for allow / deny / approval precedence

### Task 4: command runner
- implement safe-ish local subprocess execution with timeout support
- capture stdout/stderr/exit code/duration

### Task 5: trace store
- append JSONL traces
- fetch by run id
- tests for persistence

### Task 6: API
- implement FastAPI endpoints
- return structured responses for all policy outcomes
- tests with TestClient

### Task 7: CLI
- implement `serve` and `run`

### Task 8: polish
- example policy file
- improve README
- run tests

## Verification
Use these commands when ready:
- `python3 -m pip install -e '.[dev]'`
- `pytest -q`
- `python3 -m repoexec.cli run --workspace . --command 'echo hello' --policy examples/policy.json`

## Success criteria
The repo is successful for MVP if:
- tests pass
- README clearly explains the idea
- a user can start the server and submit a run
- approval-required and denied commands return correct structured responses
- executed commands are persisted to a trace log
