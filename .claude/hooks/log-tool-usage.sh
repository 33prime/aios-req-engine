#!/usr/bin/env bash
# PreToolUse hook — logs tool invocations to ~/.claude/skill-usage.log
# Runs async, never blocks (exit 0 always)

set -euo pipefail

LOG_FILE="$HOME/.claude/skill-usage.log"

# Read JSON from stdin
INPUT=$(cat)

# Extract tool name using jq (if available) or fallback to grep
if command -v jq &>/dev/null; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "unknown"' 2>/dev/null || echo "unknown")
else
  TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' || echo "unknown")
fi

# Get session ID from env or generate one
SESSION_ID="${CLAUDE_SESSION_ID:-${PPID:-unknown}}"

# Append to log: timestamp \t session_id \t tool_name
echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ')\t${SESSION_ID}\t${TOOL_NAME}" >> "$LOG_FILE"

exit 0
