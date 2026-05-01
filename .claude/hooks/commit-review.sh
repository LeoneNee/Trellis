#!/usr/bin/env bash
# Pre-commit review wrapper - runs multi-agent review via Codex CLI + Kimi CLI
# Called from settings.json Bash(git commit*) hook

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REVIEW_WRAPPER="${SCRIPT_DIR}/../skills/multi-review/scripts/review_wrapper.py"

if [ ! -f "$REVIEW_WRAPPER" ]; then
  exit 0
fi

# Get staged diff content
DIFF_CONTENT=$(git diff --cached -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' '*.go' '*.java' '*.rs' 2>/dev/null || true)

# Skip review if no staged changes
if [ -z "$DIFF_CONTENT" ]; then
  exit 0
fi

# Get commit message from env or fall back to last commit
COMMIT_MSG=''
if [ -n "${CLAUDE_USER_INPUT:-}" ]; then
  COMMIT_MSG=$(printf '%s' "${CLAUDE_USER_INPUT:-}" | head -c 100)
fi
if [ -z "$COMMIT_MSG" ]; then
  COMMIT_MSG=$(head -c 100 .git/COMMIT_EDITMSG 2>/dev/null || git log -1 --format=%s 2>/dev/null | head -c 100 || true)
fi

printf '%s\n' "$DIFF_CONTENT" | python3 "$REVIEW_WRAPPER" --message "$COMMIT_MSG"
