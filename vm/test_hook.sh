#!/usr/bin/env bash
# Test the post-push hook locally without actually pushing
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find the actual .git directory (could be a worktree)
if [[ -f "$ROOT_DIR/.git" ]]; then
  GIT_DIR=$(cat "$ROOT_DIR/.git" | sed 's/gitdir: //')
  HOOK_DIR=$(dirname "$GIT_DIR")/hooks
else
  HOOK_DIR="$ROOT_DIR/.git/hooks"
fi

HOOK_FILE="$HOOK_DIR/post-push"

if [[ ! -f "$HOOK_FILE" ]]; then
  echo "❌ Hook not found at $HOOK_FILE"
  exit 1
fi

if [[ ! -x "$HOOK_FILE" ]]; then
  echo "❌ Hook exists but is not executable: $HOOK_FILE"
  echo "Run: chmod +x $HOOK_FILE"
  exit 1
fi

echo "🧪 Testing post-push hook..."
echo "📍 Hook location: $HOOK_FILE"
echo ""

# Simulate the hook input (pushing main branch to origin)
echo "refs/heads/main 0000000000000000000000000000000000000000 refs/heads/main 0000000000000000000000000000000000000000" | "$HOOK_FILE"

exit_code=$?

if [[ $exit_code -eq 0 ]]; then
  echo ""
  echo "✅ Hook test completed successfully"
else
  echo ""
  echo "❌ Hook test failed with exit code $exit_code"
fi

exit $exit_code
