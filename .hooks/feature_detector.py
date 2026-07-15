#!/usr/bin/env python3
"""Feature detection hook — analyzes commits for integration-relevant changes."""
import sys
import argparse
import json
from pathlib import Path

TRACKING_FILE = Path(".feature_tracking.json")

FEATURE_PATTERNS = [
    ("api_endpoint", r"(router|app)\.(get|post|put|delete|patch)\("),
    ("new_model", r"class\s+\w+(Model|Schema|Entity)\b"),
    ("migration", r"(migrate|migration|alembic)"),
    ("contract", r"(contract|solidity|forge)"),
]


def detect(commit: str, files: list[str], min_confidence: float) -> int:
    detected = []
    for fname in files:
        fpath = Path(fname)
        if not fpath.exists():
            continue
        try:
            content = fpath.read_text(errors="replace")
        except (OSError, PermissionError):
            continue
        for feature_name, pattern in FEATURE_PATTERNS:
            import re
            if re.search(pattern, content):
                detected.append({"feature": feature_name, "file": fname, "confidence": 0.8})

    tracking = {"commit": commit, "detected": detected}
    TRACKING_FILE.write_text(json.dumps(tracking, indent=2))

    if detected:
        print(f"Detected {len(detected)} feature(s) in commit {commit[:8]}")
        for d in detected:
            print(f"  [{d['confidence']:.0%}] {d['feature']} in {d['file']}")
        return 1  # trigger integration check
    print(f"✓ No new features requiring integration check in {commit[:8]}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Feature detector")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--files", default="")
    parser.add_argument("--min-confidence", type=float, default=0.7)
    args = parser.parse_args()
    files = [f for f in args.files.split() if f]
    return detect(args.commit, files, args.min_confidence)


if __name__ == "__main__":
    sys.exit(main())
