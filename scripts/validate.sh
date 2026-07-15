#!/usr/bin/env bash
# ADR pipeline validation
set -euo pipefail

MODE="${1:-adr}"

case "$MODE" in
  adr)
    echo "Validating ADR pipeline..."
    # Verify required ADR directories exist
    for dir in adr/proposed adr/accepted; do
      if [ ! -d "$dir" ]; then
        echo "❌ Missing directory: $dir"
        exit 1
      fi
    done
    echo "✓ ADR pipeline validation passed"
    ;;
  chain)
    python3 .chain/chain_manager.py verify
    ;;
  stf)
    echo "Validating STF compliance..."
    [ -f ".stf/neutron.stf" ] || { echo "❌ Missing .stf/neutron.stf"; exit 1; }
    echo "✓ STF validation passed"
    ;;
  *)
    echo "Usage: $0 [adr|chain|stf]"
    exit 1
    ;;
esac
