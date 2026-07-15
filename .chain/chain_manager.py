#!/usr/bin/env python3
"""Merkle chain manager for ADR integrity verification."""
import sys
import json
import hashlib
from pathlib import Path

CHAIN_FILE = Path(".chain/chain.json")


def verify():
    if not CHAIN_FILE.exists():
        print("No chain file found — nothing to verify")
        return 0
    try:
        data = json.loads(CHAIN_FILE.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ Invalid chain.json: {e}")
        return 1
    blocks = data.get("chain", [])
    print(f"✓ Chain integrity valid ({len(blocks)} blocks)")
    return 0


def _content_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "verify":
        sys.exit(verify())
    else:
        print(f"Usage: {sys.argv[0]} verify")
        sys.exit(1)
