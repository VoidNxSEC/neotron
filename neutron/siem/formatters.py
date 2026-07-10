"""
SIEM Format Converters — Neotron events → standard SIEM formats.

Formats:
  CEF  (Common Event Format)      — ArcSight, Splunk Enterprise
  LEEF (Log Event Extended Format) — IBM QRadar
  JSON (structured)               — Elasticsearch, Owasaka, custom
  Syslog RFC 5424                 — Standard syslog with structured data
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# SIEM Event Model
# ---------------------------------------------------------------------------


class SIEMSeverity(Enum):
    """Maps Neotron severity levels to SIEM severity integers (0-10)."""

    DEBUG = 0
    INFO = 2
    LOW = 3
    MEDIUM = 5
    HIGH = 7
    CRITICAL = 9
    BLOCK = 10


# Map Neotron guardrail severity → SIEM severity
SEVERITY_MAP: dict[str, SIEMSeverity] = {
    "debug": SIEMSeverity.DEBUG,
    "info": SIEMSeverity.INFO,
    "warn": SIEMSeverity.LOW,
    "low": SIEMSeverity.LOW,
    "medium": SIEMSeverity.MEDIUM,
    "high": SIEMSeverity.HIGH,
    "critical": SIEMSeverity.CRITICAL,
    "block": SIEMSeverity.BLOCK,
}


@dataclass
class SIEMEvent:
    """
    Normalized SIEM event from a Neotron compliance event.

    This is the canonical intermediate representation — all formatters
    consume this and produce their respective output format.

    CEF key mapping:
      - vendor: "Neotron"
      - product: "NEXUS"
      - version: "1.0"
      - signature: guardrail_name
      - name: "{regulation} - {guardrail_name}"
      - severity: mapped 0-10
      - extension fields: all metadata
    """

    # Required CEF header fields
    vendor: str = "Neotron"
    product: str = "NEXUS"
    version: str = "1.0"
    signature: str = ""
    name: str = ""
    severity: SIEMSeverity = SIEMSeverity.INFO

    # Event metadata
    timestamp: str = ""
    source_hostname: str = ""
    source_service: str = "neotron"
    message: str = ""
    raw_event: dict[str, Any] = field(default_factory=dict)

    # Extension fields (CEF key=value pairs)
    extensions: dict[str, str] = field(default_factory=dict)

    # NATS subject for routing
    nats_subject: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if not self.source_hostname:
            self.source_hostname = socket.gethostname()
        if not self.name and self.signature:
            self.name = self.signature

    @classmethod
    def from_compliance_event(cls, event: dict[str, Any]) -> SIEMEvent:
        """
        Convert a Neotron compliance event dict → SIEMEvent.

        Expected event fields (from AuditLogger / compliance.events):
          - guardrail_name: str
          - regulation: str (LGPD, GDPR, etc.)
          - severity: str
          - passed: bool
          - audit_id: int
          - agent_output_hash: str
          - details: str
          - metadata: dict
          - subject: str (NATS subject)
          - timestamp: str
          - confidence: float
        """
        guardrail = event.get("guardrail_name", "unknown")
        regulation = event.get("regulation", "N/A")
        sev = event.get("severity", "info")
        passed = event.get("passed", True)
        violation = not passed

        # Build extensions (CEF key=value pairs)
        extensions: dict[str, str] = {
            "auditId": str(event.get("audit_id", "")),
            "regulation": regulation,
            "guardrail": guardrail,
            "passed": str(passed).lower(),
            "source": event.get("source", "neotron"),
        }

        if "agent_output_hash" in event:
            extensions["outputHash"] = str(event["agent_output_hash"])
        if "confidence" in event:
            extensions["confidence"] = str(event["confidence"])
        if "details" in event:
            extensions["details"] = str(event["details"])[:1023]

        # Add any extra metadata as flat keys
        meta = event.get("metadata") or {}
        if isinstance(meta, dict):
            for k, v in meta.items():
                if k not in extensions:
                    extensions[str(k)] = str(v)[:1023]

        severity_enum = SEVERITY_MAP.get(sev, SIEMSeverity.MEDIUM)
        if violation and severity_enum.value < SIEMSeverity.HIGH.value:
            severity_enum = SIEMSeverity.HIGH

        return cls(
            vendor="Neotron",
            product="NEXUS",
            version="1.0",
            signature=guardrail,
            name=f"{regulation} - {guardrail}",
            severity=severity_enum,
            timestamp=event.get("timestamp", ""),
            source_service="neotron",
            message=event.get("details", guardrail),
            raw_event=event,
            extensions=extensions,
            nats_subject=event.get("subject", ""),
        )


# ---------------------------------------------------------------------------
# CEF (Common Event Format) — ArcSight, Splunk
# ---------------------------------------------------------------------------

# Characters that must be escaped in CEF extension values
_CEF_ESCAPE_MAP = str.maketrans(
    {
        "\\": "\\\\",
        "=": "\\=",
        "\n": "\\n",
        "\r": "\\r",
    }
)


def _escape_cef(value: str) -> str:
    """Escape special characters for CEF extension values."""
    return value.translate(_CEF_ESCAPE_MAP)


def format_cef(event: SIEMEvent) -> str:
    """
    Format a SIEMEvent as a CEF (Common Event Format) string.

    CEF Format:
      CEF:Version|Device Vendor|Device Product|Device Version|
      Signature ID|Name|Severity|Extension

    Reference: ArcSight CEF Implementation Guide

    Example:
      CEF:0|Neotron|NEXUS|1.0|lgpd_art18_explanation|
      LGPD - lgpd_art18_explanation|7|auditId=42 regulation=LGPD ...
    """
    # CEF Header (pipe-separated, prefix "CEF:0")
    header = "|".join(
        [
            "CEF:0",
            _escape_cef(event.vendor),
            _escape_cef(event.product),
            _escape_cef(event.version),
            _escape_cef(event.signature),
            _escape_cef(event.name),
            str(event.severity.value),
        ]
    )

    # CEF Extensions (space-separated key=value)
    ext_pairs = []
    for key, value in event.extensions.items():
        safe_key = _escape_cef(key)
        safe_val = _escape_cef(value)
        ext_pairs.append(f"{safe_key}={safe_val}")

    # Add standard CEF extension fields
    ext_pairs.insert(0, f"rt={event.timestamp}")
    ext_pairs.insert(0, f"dhost={_escape_cef(event.source_hostname)}")
    ext_pairs.insert(0, f"dvchost={_escape_cef(event.source_hostname)}")
    ext_pairs.insert(0, f"msg={_escape_cef(event.message[:1023])}")

    extensions_str = " ".join(ext_pairs)

    return f"{header}|{extensions_str}"


# ---------------------------------------------------------------------------
# LEEF (Log Event Extended Format) — IBM QRadar
# ---------------------------------------------------------------------------


def format_leef(event: SIEMEvent) -> str:
    """
    Format a SIEMEvent as LEEF (Log Event Extended Format).

    LEEF Format:
      LEEF:2.0|Vendor|Product|Version|EventID|^|
      key1=value1^key2=value2

    Reference: IBM QRadar LEEF Guide

    Example:
      LEEF:2.0|Neotron|NEXUS|1.0|lgpd_art18_explanation|^|
      severity=7^auditId=42^regulation=LGPD
    """
    header = "|".join(
        [
            "LEEF:2.0",
            event.vendor,
            event.product,
            event.version,
            event.signature,
            "^",
        ]
    )

    attrs = [
        f"sev={event.severity.value}",
        f"cat={event.signature}",
        f"msg={event.message[:1023]}",
        f"devTime={event.timestamp}",
        f"src={event.source_hostname}",
    ]

    for key, value in event.extensions.items():
        # LEEF uses caret (^) as delimiter, so escape it
        safe_key = str(key).replace("^", "\\^").replace("=", "\\=")
        safe_val = str(value).replace("^", "\\^").replace("=", "\\=")
        attrs.append(f"{safe_key}={safe_val}")

    return f"{header}{'^'.join(attrs)}"


# ---------------------------------------------------------------------------
# JSON (structured) — Elasticsearch, Owasaka, custom
# ---------------------------------------------------------------------------


def format_json(event: SIEMEvent) -> str:
    """
    Format a SIEMEvent as a structured JSON string (one line).

    Produces a normalized JSON document suitable for:
      - Elasticsearch / OpenSearch bulk ingest
      - Owasaka SIEM (via NATS)
      - Splunk HTTP Event Collector (HEC)
      - Custom SIEM pipelines
    """
    doc: dict[str, Any] = {
        "@timestamp": event.timestamp,
        "event": {
            "provider": event.vendor,
            "product": event.product,
            "kind": "event",
            "category": "compliance",
            "action": event.signature,
            "severity": event.severity.value,
            "outcome": "failure" if event.severity.value >= 7 else "success",
        },
        "host": {
            "hostname": event.source_hostname,
            "name": event.source_hostname,
        },
        "service": {
            "name": event.source_service,
        },
        "message": event.message,
        "labels": {k: v for k, v in event.extensions.items()},
        "neotron": event.raw_event,
    }

    return json.dumps(doc, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Syslog RFC 5424 — Standard syslog with structured data
# ---------------------------------------------------------------------------

# RFC 5424 facility codes
FACILITY = {
    "kern": 0,
    "user": 1,
    "mail": 2,
    "daemon": 3,
    "auth": 4,
    "syslog": 5,
    "lpr": 6,
    "news": 7,
    "uucp": 8,
    "cron": 9,
    "authpriv": 10,
    "ftp": 11,
    "local0": 16,
    "local1": 17,
    "local2": 18,
    "local3": 19,
    "local4": 20,
    "local5": 21,
    "local6": 22,
    "local7": 23,
}

# RFC 5424 severity codes (map from 0-10 to 0-7)
SEVERITY_SYSLOG = {
    0: 7,  # DEBUG → debug
    1: 6,  # INFO → info
    2: 6,
    3: 5,  # LOW → notice
    4: 4,  # MEDIUM → warning
    5: 4,
    6: 3,  # HIGH → err
    7: 3,
    8: 2,  # CRITICAL → crit
    9: 2,
    10: 1,  # BLOCK → alert
}


def format_syslog_rfc5424(
    event: SIEMEvent,
    facility: str = "local0",
    app_name: str = "neotron",
    msgid: str = "COMPLIANCE",
) -> str:
    """
    Format as Syslog RFC 5424 message.

    RFC 5424 Format:
      <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID
      [SD-ID@enterprise-id key="value" ...] BODY

    PRI = facility * 8 + severity

    Example:
      <134>1 2026-04-07T14:33:00.000Z neotron-host neotron 1234 COMPLIANCE
      [neotron@55808 auditId="42" regulation="LGPD"] LGPD compliance check
    """
    facility_code = FACILITY.get(facility, FACILITY["local0"])
    syslog_sev = SEVERITY_SYSLOG.get(event.severity.value, 5)
    pri = facility_code * 8 + syslog_sev

    # Structured data: [neotron@55808 key="value" ...]
    sd_pairs = []
    for key, value in event.extensions.items():
        safe_key = str(key).replace('"', '\\"').replace("]", "\\]")
        safe_val = str(value).replace('"', '\\"').replace("]", "\\]")
        sd_pairs.append(f'{safe_key}="{safe_val}"')

    # Additional standard structured data
    sd_pairs.insert(0, f'severity="{event.severity.value}"')
    sd_pairs.insert(0, f'signature="{event.signature}"')

    structured_data = f"[neotron@55808 {' '.join(sd_pairs)}]"

    return (
        f"<{pri}>1 {event.timestamp} {event.source_hostname} "
        f"{app_name} - {msgid} "
        f"{structured_data} {event.message}"
    )
