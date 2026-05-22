#!/usr/bin/env bash
# Example: a coding agent submits commands through RepoExec instead of running shell directly.
set -euo pipefail

REPOEXEC_HOST="${REPOEXEC_HOST:-127.0.0.1:8765}"
WORKSPACE="${WORKSPACE:-.}"
POLICY="${POLICY:-examples/policy.json}"

echo "==> Starting RepoExec (background)"
python3 -m repoexec.cli serve --policy "$POLICY" --host 127.0.0.1 --port 8765 &
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
