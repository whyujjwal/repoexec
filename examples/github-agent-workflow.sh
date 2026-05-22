#!/usr/bin/env bash
# Example: a coding agent submits commands through RepoExec instead of running shell directly.
set -euo pipefail

REPOEXEC_HOST="${REPOEXEC_HOST:-127.0.0.1:8765}"
WORKSPACE="${WORKSPACE:-.}"
POLICY="${POLICY:-examples/policy.json}"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "python3 is required." >&2
  exit 1
fi

if [ -x ".venv/bin/repoexec" ]; then
  REPOEXEC=".venv/bin/repoexec"
elif command -v repoexec >/dev/null 2>&1; then
  REPOEXEC="repoexec"
else
  echo "Install RepoExec first: python3 -m pip install -e '.[dev]'" >&2
  exit 1
fi

if [ "$REPOEXEC_HOST" = "127.0.0.1:8765" ]; then
  PORT="$("$PYTHON" -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1]); s.close()")"
  REPOEXEC_HOST="127.0.0.1:${PORT}"
fi

HOST="${REPOEXEC_HOST%:*}"
PORT="${REPOEXEC_HOST##*:}"

echo "==> Starting RepoExec (background) on ${REPOEXEC_HOST}"
"$REPOEXEC" serve --policy "$POLICY" --host "$HOST" --port "$PORT" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
sleep 1

submit() {
  local command="$1"
  curl -s -X POST "http://${REPOEXEC_HOST}/runs" \
    -H 'Content-Type: application/json' \
    -d "{\"workspace\": \"${WORKSPACE}\", \"command\": \"${command}\", \"metadata\": {\"agent\": \"demo\"}}"
}

echo
echo "==> Safe read-only command (allowed)"
submit "git status --short" | python3 -m json.tool

echo
echo "==> Destructive command (denied by policy)"
submit "rm -rf /tmp/demo" | python3 -m json.tool

echo
echo "==> Publish command (approval required)"
submit "git push origin main" | python3 -m json.tool

echo
echo "==> Recent traces"
curl -s "http://${REPOEXEC_HOST}/runs?limit=3" | python3 -m json.tool
