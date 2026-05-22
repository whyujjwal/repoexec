# RepoExec Roadmap

## Shipped in MVP+
- policy engine for allow/deny/approval-required with explanation output
- local shell execution in a workspace with timeout support
- JSONL trace persistence with in-memory index
- FastAPI API (`/healthz`, `/runs`, `/runs/{id}`, `/runs/{id}/replay`)
- Typer CLI (`serve`, `run`, `replay`, `traces list/get`)
- trace listing and replay support
- workspace validation and empty-command guard
- configurable workspace root constraints (path-escape prevention)
- GitHub Actions CI workflow (`.github/workflows/ci.yml`, ready to push)
- README with architecture and agent integration examples

## Next improvements
1. Add approval tokens / signed approvals for `require_approval` commands.
2. Add richer trace viewer UI or TUI.
3. Add GitHub App / webhook integration for repo-scoped execution.
4. Add pluggable policy backends (OPA, remote config).
5. Add streaming stdout/stderr for long-running commands.

## Stretch ideas
- browser execution layer
- multi-tenant auth and RBAC
- remote worker pool
- MCP server wrapper for RepoExec
