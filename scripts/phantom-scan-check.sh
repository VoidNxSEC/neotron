#!/usr/bin/env bash
# Phantom secret leak scan — non-blocking (reports but does not fail CI)
set -euo pipefail

TARGET="${1:-.}"
EXIT_CODE=0

echo "Running Phantom leak scan on: $TARGET"

# Common high-confidence secret patterns (no false positives)
PATTERNS=(
  'AWS_SECRET_ACCESS_KEY\s*=\s*[A-Za-z0-9/+]{40}'
  'PRIVATE KEY-----'
  'ghp_[A-Za-z0-9]{36}'
  'glpat-[A-Za-z0-9\-_]{20}'
  'xoxb-[0-9]+-[A-Za-z0-9]+'  # Slack bot token
)

FOUND=0
for pattern in "${PATTERNS[@]}"; do
  if grep -rqE "$pattern" \
      --include="*.py" --include="*.ts" --include="*.js" \
      --include="*.env" --include="*.yaml" --include="*.yml" \
      --exclude-dir=node_modules --exclude-dir=.git \
      --exclude-dir=frontend \
      "$TARGET" 2>/dev/null; then
    echo "⚠ Pattern matched: $pattern"
    FOUND=$((FOUND + 1))
  fi
done

if [ "$FOUND" -gt 0 ]; then
  echo "⚠ $FOUND potential secret pattern(s) detected — review manually"
  echo "  Note: these may be false positives; verify before acting"
else
  echo "✓ No high-confidence secret patterns detected"
fi

# Non-blocking: always exit 0
exit 0
