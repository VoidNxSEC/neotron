"""
NATS Bridge Type Mapping — Python ↔ Rust (SPECTRE) Event Schemas.

This module defines the canonical event type schemas that are shared
between Neotron (Python) and SPECTRE (Rust). Each event type has a
Python dataclass representation that serializes to the exact JSON
shape expected by spectre-events.

Schema synchronization:
  - Source of truth: spectre-events crate (Rust)
  - Python mirror: this module
  - Validation: both sides validate on publish/subscribe

When adding a new event type:
  1. Define it in spectre-events (Rust)
  2. Mirror it here (Python dataclass + schema)
  3. Add to EVENT_REGISTRY
  4. Run integration test: bridge/test_nats_bridge.py
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ============================================================================
# Event Type Registry
# ============================================================================


class EventVersion(Enum):
    """Event schema versions for compatibility checks."""

    V1_0 = "1.0"


@dataclass
class EventTypeInfo:
    """Metadata for a registered event type."""

    name: str
    subject: str
    version: EventVersion = EventVersion.V1_0
    description: str = ""
    source: str = "neotron"  # or "spectre"


# Complete registry of all event types crossing the NATS bridge
EVENT_REGISTRY: dict[str, EventTypeInfo] = {
    # ── Compliance Layer 1: SENTINEL ──
    "sentinel_check": EventTypeInfo(
        name="sentinel_check",
        subject="neotron.compliance.sentinel.v1",
        description="SENTINEL guardrail application-layer check result",
    ),
    "sentinel_violation": EventTypeInfo(
        name="sentinel_violation",
        subject="neotron.compliance.violation.v1",
        description="SENTINEL guardrail violation (block/critical/high)",
    ),
    # ── Compliance Layer 2: BASTION ──
    "bastion_enforce": EventTypeInfo(
        name="bastion_enforce",
        subject="neotron.compliance.bastion.v1",
        description="BASTION kernel-level enforcement event (Landlock/seccomp)",
    ),
    # ── Compliance Layer 3: CORTEX ──
    "cortex_consensus": EventTypeInfo(
        name="cortex_consensus",
        subject="neotron.cortex.consensus.v1",
        description="CORTEX multi-agent swarm consensus decision",
    ),
    # ── SIEM Export ──
    "siem_export": EventTypeInfo(
        name="siem_export",
        subject="neotron.siem.export.v1",
        description="SIEM export event (CEF/LEEF/JSON/Syslog)",
    ),
    # ── Audit Trail ──
    "audit_log": EventTypeInfo(
        name="audit_log",
        subject="neotron.audit.log.v1",
        description="Immutable audit log entry",
    ),
    # ── License Verification (IP Guard) ──
    "license_verify_request": EventTypeInfo(
        name="license_verify_request",
        subject="ipguard.license.verify.v1",
        description="License verification request (Neotron → IP Guard)",
    ),
    "license_verify_result": EventTypeInfo(
        name="license_verify_result",
        subject="ipguard.license.result.v1",
        description="License verification result (IP Guard → Neotron)",
        source="ip-guard",
    ),
    # ── SPECTRE Events ──
    "spectre_health": EventTypeInfo(
        name="spectre_health",
        subject="spectre.health.v1",
        description="SPECTRE proxy health check",
        source="spectre",
    ),
    "spectre_secret_rotation": EventTypeInfo(
        name="spectre_secret_rotation",
        subject="spectre.secrets.rotation.v1",
        description="SPECTRE secret rotation event",
        source="spectre",
    ),
}


def list_event_types(source: str | None = None) -> list[EventTypeInfo]:
    """List registered event types, optionally filtered by source."""
    if source:
        return [e for e in EVENT_REGISTRY.values() if e.source == source]
    return list(EVENT_REGISTRY.values())


# ============================================================================
# Canonical Event Schemas (Python ↔ Rust)
# ============================================================================


@dataclass
class ComplianceEvent:
    """
    Canonical compliance event — mirrors spectre-events ComplianceEvent.

    This is the standard envelope for all compliance-related events
    crossing the NATS bridge between Neotron and SPECTRE.

    Rust equivalent:
      pub struct ComplianceEvent {
          pub audit_id: u64,
          pub guardrail_name: String,
          pub regulation: String,
          pub severity: Severity,
          pub passed: bool,
          pub confidence: f64,
          pub agent_output_hash: String,
          pub details: String,
          pub agent_id: String,
          pub risk_score: f64,
          pub reputation: f64,
          pub metadata: HashMap<String, String>,
          pub timestamp: String,
          pub source: String,
          pub subject: String,
      }
    """

    audit_id: int = 0
    guardrail_name: str = "unknown"
    regulation: str = "N/A"
    severity: str = "info"  # debug, info, low, medium, high, critical, block
    passed: bool = True
    confidence: float = 0.0
    agent_output_hash: str = ""
    details: str = ""
    agent_id: str = ""
    risk_score: float = 0.0
    reputation: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)
    timestamp: str = ""
    source: str = "neotron"
    subject: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict for NATS publish."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComplianceEvent:
        """Deserialize from NATS message payload."""
        return cls(
            audit_id=int(data.get("audit_id", 0)),
            guardrail_name=str(data.get("guardrail_name", "unknown")),
            regulation=str(data.get("regulation", "N/A")),
            severity=str(data.get("severity", "info")),
            passed=bool(data.get("passed", True)),
            confidence=float(data.get("confidence", 0.0)),
            agent_output_hash=str(data.get("agent_output_hash", "")),
            details=str(data.get("details", "")),
            agent_id=str(data.get("agent_id", "")),
            risk_score=float(data.get("risk_score", 0.0)),
            reputation=float(data.get("reputation", 0.0)),
            metadata=data.get("metadata", {}),
            timestamp=str(data.get("timestamp", "")),
            source=str(data.get("source", "neotron")),
            subject=str(data.get("subject", "")),
        )

    def is_violation(self) -> bool:
        """Check if this event represents a compliance violation."""
        return (not self.passed) and self.severity in ("block", "critical", "high")


@dataclass
class LicenseVerifyRequest:
    """
    License verification request — Neotron → IP Guard.

    Rust equivalent:
      pub struct LicenseVerifyRequest {
          pub flake_path: String,
          pub package_name: String,
          pub store_hash: String,
          pub request_id: String,
          pub timestamp: String,
      }
    """

    flake_path: str = ""
    package_name: str = ""
    store_hash: str = ""
    request_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.request_id:
            import uuid

            self.request_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LicenseVerifyRequest:
        return cls(
            flake_path=str(data.get("flake_path", "")),
            package_name=str(data.get("package_name", "")),
            store_hash=str(data.get("store_hash", "")),
            request_id=str(data.get("request_id", "")),
            timestamp=str(data.get("timestamp", "")),
        )


@dataclass
class LicenseVerifyResult:
    """
    License verification result — IP Guard → Neotron.

    Rust equivalent:
      pub struct LicenseVerifyResult {
          pub request_id: String,
          pub package_name: String,
          pub store_hash: String,
          pub license_spdx: String,
          pub token_id: u64,
          pub compliant: bool,
          pub proof_hash: String,
          pub tx_hash: String,
          pub timestamp: String,
          pub errors: Vec<String>,
      }
    """

    request_id: str = ""
    package_name: str = ""
    store_hash: str = ""
    license_spdx: str = ""
    token_id: int = 0
    compliant: bool = False
    proof_hash: str = ""
    tx_hash: str = ""
    timestamp: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LicenseVerifyResult:
        return cls(
            request_id=str(data.get("request_id", "")),
            package_name=str(data.get("package_name", "")),
            store_hash=str(data.get("store_hash", "")),
            license_spdx=str(data.get("license_spdx", "")),
            token_id=int(data.get("token_id", 0)),
            compliant=bool(data.get("compliant", False)),
            proof_hash=str(data.get("proof_hash", "")),
            tx_hash=str(data.get("tx_hash", "")),
            timestamp=str(data.get("timestamp", "")),
            errors=list(data.get("errors", [])),
        )


@dataclass
class SIEMExportEvent:
    """
    SIEM export event envelope.

    Sent when compliance events are exported to external SIEM systems.
    """

    format: str = "json"  # cef, leef, json, syslog
    target: str = "file"  # file, syslog, nats
    event_count: int = 0
    bytes_written: int = 0
    filepath: str = ""
    timestamp: str = ""
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SIEMExportEvent:
        return cls(
            format=str(data.get("format", "json")),
            target=str(data.get("target", "file")),
            event_count=int(data.get("event_count", 0)),
            bytes_written=int(data.get("bytes_written", 0)),
            filepath=str(data.get("filepath", "")),
            timestamp=str(data.get("timestamp", "")),
            errors=list(data.get("errors", [])),
        )


@dataclass
class SpectreHealthEvent:
    """
    SPECTRE proxy health check response.

    Rust equivalent:
      pub struct HealthResponse {
          pub status: String,
          pub version: String,
          pub uptime_seconds: u64,
          pub connected_clients: u64,
      }
    """

    status: str = "unknown"
    version: str = ""
    uptime_seconds: int = 0
    connected_clients: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpectreHealthEvent:
        return cls(
            status=str(data.get("status", "unknown")),
            version=str(data.get("version", "")),
            uptime_seconds=int(data.get("uptime_seconds", 0)),
            connected_clients=int(data.get("connected_clients", 0)),
        )


# ============================================================================
# Type mapping lookup
# ============================================================================

# Maps event type names → Python dataclass
_TYPE_MAP: dict[str, type] = {
    "sentinel_check": ComplianceEvent,
    "sentinel_violation": ComplianceEvent,
    "bastion_enforce": ComplianceEvent,
    "cortex_consensus": ComplianceEvent,
    "siem_export": SIEMExportEvent,
    "audit_log": ComplianceEvent,
    "license_verify_request": LicenseVerifyRequest,
    "license_verify_result": LicenseVerifyResult,
    "spectre_health": SpectreHealthEvent,
    "spectre_secret_rotation": ComplianceEvent,
}

# Maps NATS subjects → event type names
_SUBJECT_MAP: dict[str, str] = {info.subject: name for name, info in EVENT_REGISTRY.items()}


def get_event_class(event_type: str) -> type | None:
    """Get the Python dataclass for a given event type name."""
    return _TYPE_MAP.get(event_type)


def get_event_type_for_subject(subject: str) -> str | None:
    """Get the event type name for a given NATS subject."""
    return _SUBJECT_MAP.get(subject)


def decode_event(subject: str, payload: bytes | str | dict[str, Any]) -> Any | None:
    """
    Decode a raw NATS message into the appropriate Python dataclass.

    Args:
        subject: NATS subject the message arrived on
        payload: Raw message payload (bytes, JSON string, or pre-parsed dict)

    Returns:
        Instantiated dataclass, or None if the type is unknown.

    Example:
        event = decode_event("neotron.compliance.sentinel.v1", msg.data)
        if isinstance(event, ComplianceEvent):
            print(event.guardrail_name)
    """
    event_type = get_event_type_for_subject(subject)
    if event_type is None:
        return None

    cls = get_event_class(event_type)
    if cls is None:
        return None

    # Parse payload
    if isinstance(payload, bytes):
        data = json.loads(payload.decode())
    elif isinstance(payload, str):
        data = json.loads(payload)
    else:
        data = payload

    return cls.from_dict(data)


def encode_event(event: Any, pretty: bool = False) -> bytes:
    """
    Encode a Python event dataclass to JSON bytes for NATS publish.

    Args:
        event: A dataclass instance (ComplianceEvent, LicenseVerifyRequest, etc.)
        pretty: If True, pretty-print with indentation

    Returns:
        JSON-encoded bytes
    """
    if pretty:
        return json.dumps(event.to_dict(), indent=2, default=str).encode()
    return json.dumps(event.to_dict(), separators=(",", ":"), default=str).encode()


# ============================================================================
# Schema validation helpers
# ============================================================================


def validate_event(event_type: str, payload: dict[str, Any]) -> list[str]:
    """
    Validate a payload against the expected schema for an event type.

    Returns a list of validation errors (empty = valid).
    """
    errors: list[str] = []

    info = EVENT_REGISTRY.get(event_type)
    if info is None:
        return [f"Unknown event type: {event_type}"]

    cls = get_event_class(event_type)
    if cls is None:
        return [f"No dataclass registered for event type: {event_type}"]

    # Try to instantiate — this catches type conversion errors
    try:
        cls.from_dict(payload)
    except (TypeError, ValueError) as e:
        errors.append(str(e))

    return errors


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Registry
    "EVENT_REGISTRY",
    "EventTypeInfo",
    "EventVersion",
    "list_event_types",
    # Event schemas
    "ComplianceEvent",
    "LicenseVerifyRequest",
    "LicenseVerifyResult",
    "SIEMExportEvent",
    "SpectreHealthEvent",
    # Type mapping
    "get_event_class",
    "get_event_type_for_subject",
    "decode_event",
    "encode_event",
    "validate_event",
    "_TYPE_MAP",
    "_SUBJECT_MAP",
]
