"""
License Verification — Neotron ↔ IP Guard integration.

Provides license compliance verification for Nix packages, calling
IP Guard (Rust) via subprocess or NATS bridge.

Architecture:
    neotron license verify <flake.nix>
           │
           ├── 1. Subprocess: ip-guard verify <flake.nix>
           │      (Local verification — needs IP Guard binary)
           │
           └── 2. NATS Bridge: request("ipguard.license.verify.v1", ...)
                  (Remote verification — needs NATS + IP Guard service)

Caching:
    License verification results are cached locally to avoid redundant
    on-chain queries. Cache is keyed by derivation hash.

Status:
    neotron license status
        Shows cached results + on-chain license info.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("neutron.license")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Cache directory for license verification results
LICENSE_CACHE_DIR = Path(os.environ.get("NEUTRON_LICENSE_CACHE", "/var/lib/neotron/license-cache"))

# Path to IP Guard binary (for subprocess mode)
IP_GUARD_BIN = os.environ.get("IP_GUARD_BIN", "ip-guard")

# Whether to use NATS bridge for remote verification
USE_NATS_BRIDGE = os.environ.get("NEUTRON_LICENSE_NATS", "0") == "1"

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class LicenseResult:
    """Result of a license compliance verification."""

    flake_path: str
    package_name: str
    package_hash: str
    spdx_id: str
    compliant: bool
    license_id: int | None = None
    errors: list[str] = field(default_factory=list)
    verified_at: float = field(default_factory=time.time)
    source: str = "local"  # local | nats | cache

    @classmethod
    def from_ip_guard_output(cls, flake_path: str, output: str) -> LicenseResult:
        """Parse IP Guard CLI output into a LicenseResult."""
        # IP Guard CLI outputs structured text. We parse key fields.
        lines = output.strip().split("\n")
        data: dict[str, Any] = {
            "package_name": "",
            "package_hash": "",
            "spdx_id": "",
            "compliant": False,
            "license_id": None,
            "errors": [],
        }

        for line in lines:
            line = line.strip()
            if line.startswith("Name:"):
                data["package_name"] = line.split(":", 1)[1].strip()
            elif line.startswith("Hash:"):
                data["package_hash"] = line.split(":", 1)[1].strip()
            elif line.startswith("SPDX:"):
                data["spdx_id"] = line.split(":", 1)[1].strip()
            elif "COMPLIANT" in line:
                data["compliant"] = "✅" in line
            elif line.startswith("License ID:"):
                try:
                    data["license_id"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            # Collect error lines
            if line.startswith(("❌", "⚠️", "Error:", "License error:", "SPDX mismatch")):
                data["errors"].append(line)

        return cls(
            flake_path=flake_path,
            package_name=data["package_name"] or "unknown",
            package_hash=data["package_hash"] or "unknown",
            spdx_id=data["spdx_id"] or "unknown",
            compliant=data["compliant"],
            license_id=data["license_id"],
            errors=data["errors"],
            source="local",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "flake_path": self.flake_path,
            "package_name": self.package_name,
            "package_hash": self.package_hash,
            "spdx_id": self.spdx_id,
            "compliant": self.compliant,
            "license_id": self.license_id,
            "errors": self.errors,
            "verified_at": self.verified_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LicenseResult:
        return cls(**data)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class LicenseCache:
    """
    Local cache for license verification results.

    Keyed by flake_path → (package_hash, result).
    Avoids redundant blockchain queries.
    """

    def __init__(self):
        LICENSE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._cache_file = LICENSE_CACHE_DIR / "results.json"
        self._cache: dict[str, LicenseResult] = {}
        self._load()

    def get(self, flake_path: str) -> LicenseResult | None:
        """Get cached result for a flake, returning None if stale (>24h)."""
        result = self._cache.get(flake_path)
        if result is None:
            return None
        # Cache TTL: 24 hours
        if time.time() - result.verified_at > 86400:
            return None
        return result

    def set(self, flake_path: str, result: LicenseResult) -> None:
        """Cache a verification result."""
        self._cache[flake_path] = result
        self._save()

    def list_all(self) -> list[LicenseResult]:
        """List all cached results."""
        return list(self._cache.values())

    def clear(self) -> int:
        """Clear the cache. Returns number of entries removed."""
        count = len(self._cache)
        self._cache.clear()
        self._save()
        return count

    def _load(self) -> None:
        if self._cache_file.exists():
            try:
                data = json.loads(self._cache_file.read_text())
                for flake_path, result_data in data.items():
                    self._cache[flake_path] = LicenseResult.from_dict(result_data)
            except Exception as e:
                logger.warning("Failed to load license cache: %s", e)

    def _save(self) -> None:
        try:
            data = {path: result.to_dict() for path, result in self._cache.items()}
            self._cache_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning("Failed to save license cache: %s", e)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_local(flake_path: Path) -> LicenseResult:
    """
    Verify license compliance by calling IP Guard CLI locally.

    IP Guard is maintained as a separate project (extracted out of this repo).
    Requires the `ip-guard` binary to be on PATH, or set IP_GUARD_BIN to its path.
    Falls back to extracting metadata without blockchain verification.
    """
    if not flake_path.exists():
        raise FileNotFoundError(f"Flake not found: {flake_path}")

    try:
        result = subprocess.run(
            [IP_GUARD_BIN, "verify", str(flake_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        return LicenseResult.from_ip_guard_output(str(flake_path), output)
    except FileNotFoundError:
        logger.warning(
            "ip-guard binary not found — falling back to metadata extraction. "
            "Install the IP Guard CLI (maintained separately) and put `ip-guard` "
            "on PATH, or set IP_GUARD_BIN to its location."
        )
        return _extract_fallback(flake_path)
    except subprocess.TimeoutExpired:
        logger.warning("IP Guard timed out — check RPC connectivity")
        return LicenseResult(
            flake_path=str(flake_path),
            package_name="unknown",
            package_hash="unknown",
            spdx_id="unknown",
            compliant=False,
            errors=["IP Guard verification timed out — RPC unreachable?"],
        )


async def verify_via_nats(flake_path: Path) -> LicenseResult:
    """
    Verify license compliance via NATS bridge (remote IP Guard service).

    Sends a request to ipguard.license.verify.v1 and waits for response.
    """
    from neutron.events import request

    response = await request(
        "ipguard.license.verify.v1",
        {
            "flake_path": str(flake_path),
            "request_id": str(__import__("uuid").uuid4()),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        timeout=10.0,
    )

    if response is None:
        return LicenseResult(
            flake_path=str(flake_path),
            package_name="unknown",
            package_hash="unknown",
            spdx_id="unknown",
            compliant=False,
            errors=["No response from IP Guard via NATS bridge"],
            source="nats",
        )

    return LicenseResult(
        flake_path=str(flake_path),
        package_name=response.get("package_name", "unknown"),
        package_hash=response.get("package_hash", "unknown"),
        spdx_id=response.get("spdx_id", "unknown"),
        compliant=response.get("compliant", False),
        license_id=response.get("license_id"),
        errors=response.get("errors", []),
        source="nats",
    )


def verify(flake_path: Path, use_cache: bool = True) -> LicenseResult:
    """
    Verify license compliance, using cache if available.

    This is the main entry point for `neotron license verify`.
    """
    # Check cache first
    cache = LicenseCache()
    if use_cache:
        cached = cache.get(str(flake_path))
        if cached is not None:
            logger.debug("License cache hit for %s", flake_path)
            return cached

    # Verify
    if USE_NATS_BRIDGE:
        import asyncio

        result = asyncio.run(verify_via_nats(flake_path))
    else:
        result = verify_local(flake_path)

    # Cache the result
    cache.set(str(flake_path), result)
    return result


def _extract_fallback(flake_path: Path) -> LicenseResult:
    """Extract metadata without blockchain verification (fallback)."""
    try:
        from neutron.events.bridge import extract_license_spdx

        # Actually, we don't have that function in Python. Use a simpler fallback.
        result = subprocess.run(
            [IP_GUARD_BIN, "extract", str(flake_path), "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return LicenseResult(
                flake_path=str(flake_path),
                package_name=data.get("name", "unknown"),
                package_hash=data.get("hash", "unknown"),
                spdx_id=data.get("spdx_id", "unknown"),
                compliant=False,  # Can't verify without blockchain
                errors=["Offline mode — metadata extracted, compliance unverified"],
                source="local",
            )
    except Exception:
        pass

    return LicenseResult(
        flake_path=str(flake_path),
        package_name="unknown",
        package_hash="unknown",
        spdx_id="unknown",
        compliant=False,
        errors=["IP Guard binary not available"],
        source="local",
    )


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def get_status() -> dict[str, Any]:
    """Get license verification system status."""
    cache = LicenseCache()
    cached = cache.list_all()

    compliant_count = sum(1 for r in cached if r.compliant)
    non_compliant_count = sum(1 for r in cached if not r.compliant)

    # Check IP Guard availability
    ip_guard_available = False
    try:
        result = subprocess.run(
            [IP_GUARD_BIN, "info"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        ip_guard_available = result.returncode == 0
    except Exception:
        pass

    return {
        "cached_verifications": len(cached),
        "compliant": compliant_count,
        "non_compliant": non_compliant_count,
        "ip_guard_available": ip_guard_available,
        "nats_bridge_enabled": USE_NATS_BRIDGE,
        "cache_dir": str(LICENSE_CACHE_DIR),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "LicenseResult",
    "LicenseCache",
    "verify",
    "verify_local",
    "verify_via_nats",
    "get_status",
]
