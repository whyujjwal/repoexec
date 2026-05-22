# RepoExec Roadmap

## Current MVP
- policy engine for allow/deny/approval-required
- local shell execution in a workspace
- JSONL trace persistence
- FastAPI API
- Typer CLI
- basic tests

## Next improvements
1. Add explicit timeout and trace path overrides to API and CLI.
2. Add replay support for stored runs.
3. Add safer command execution constraints and workspace validation.
4. Improve README with architecture, screenshots/examples, and positioning.
5. Add structured trace listing endpoint and CLI command.
6. Add policy explanation output: why a command was denied or required approval.
7. Add GitHub-oriented examples for coding-agent workflows.
8. Add CI via GitHub Actions.

## Stretch ideas
- approval tokens / signed approvals
- GitHub App integration
- browser execution layer
- pluggable policy backends
- richer trace viewer UI
