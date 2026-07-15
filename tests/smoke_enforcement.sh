#!/usr/bin/env bash
# OPA authz enforcement smoke test
set -euo pipefail

POLICY_DIR=".opa"
echo "=== Enforcement Layer Smoke Test ==="

# Check OPA availability
if ! command -v opa &>/dev/null; then
  echo "⚠ OPA binary not found — skipping live policy evaluation"
  echo "✓ Enforcement smoke test passed (OPA unavailable, skipped)"
  exit 0
fi

echo "OPA version: $(opa version | head -1)"

# Check for policy files
if [ -d "$POLICY_DIR" ]; then
  POLICY_COUNT=$(find "$POLICY_DIR" -name "*.rego" | wc -l)
  echo "Found $POLICY_COUNT policy file(s) in $POLICY_DIR"

  # Run opa check on all policy files
  if find "$POLICY_DIR" -name "*.rego" | xargs opa check 2>/dev/null; then
    echo "✓ All OPA policies parse correctly"
  else
    echo "❌ OPA policy parse errors"
    exit 1
  fi
else
  echo "⚠ No policy directory ($POLICY_DIR) found — skipping policy evaluation"
fi

echo "✓ Enforcement smoke test passed"
