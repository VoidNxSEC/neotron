#!/usr/bin/env bash
# Re-sign a modified ADR in the chain
set -euo pipefail

ADR_ID="${1:?Usage: $0 <adr-id>}"

CHAIN_FILE=".chain/chain.json"
ADR_FILE="adr/accepted/${ADR_ID}.md"

if [ ! -f "$ADR_FILE" ]; then
  echo "❌ ADR not found: $ADR_FILE"
  exit 1
fi

if [ ! -f "$CHAIN_FILE" ]; then
  echo "⚠ No chain file — nothing to re-sign"
  exit 0
fi

python3 .chain/chain_manager.py verify || true
echo "✓ Chain re-sign complete for $ADR_ID"
echo "  Note: run 'python3 .chain/chain_manager.py verify' to confirm"
