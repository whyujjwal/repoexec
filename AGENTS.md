# RepoExec Agent Instructions

- Read the plan in `docs/plans/2026-05-22-repoexec-mvp.md` before making major changes.
- Keep the MVP narrow: GitHub/coding-agent execution layer with policy checks, approvals, and run traces.
- Prefer Python 3.11 with FastAPI, Typer, and pytest.
- Make small, reviewable changes.
- Add or update tests for behavior changes.
- Prefer clear code over clever abstractions.
- Do not add external services or databases unless strictly needed for the MVP.
- Verify with the narrowest useful test command after edits.
