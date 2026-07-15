"""
SIEM Export Transports — deliver formatted events to SIEM targets.

Export targets:
  - File: write to /var/log/neotron/siem/ for agent pickup (Wazuh, Filebeat)
  - Syslog: UDP/TCP to SIEM collector
  - NATS: publish to Owasaka SIEM subjects
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from neutron.siem.formatters import (
    SIEMEvent,
    format_cef,
    format_json,
    format_leef,
    format_syslog_rfc5424,
)

logger = logging.getLogger("neutron.siem.exporters")

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------


def _default_siem_dir() -> Path:
    """Default SIEM log directory — user-writable, XDG-compliant."""
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return Path(os.environ.get("NEUTRON_SIEM_DIR", f"{base}/neotron/siem"))


DEFAULT_SIEM_LOG_DIR: Path = _default_siem_dir()
DEFAULT_SYSLOG_HOST = os.environ.get("NEUTRON_SYSLOG_HOST", "localhost")
DEFAULT_SYSLOG_PORT = int(os.environ.get("NEUTRON_SYSLOG_PORT", "514"))
DEFAULT_SYSLOG_PROTO = os.environ.get("NEUTRON_SYSLOG_PROTO", "udp")

# NATS subject mapping — publishes to existing compliance subjects
NATS_SIEM_SUBJECT = "neotron.compliance.siem.v1"


# ---------------------------------------------------------------------------
# SIEM Exporter — unified interface
# ---------------------------------------------------------------------------


@dataclass
class SIEMExporter:
    """
    Unified SIEM exporter supporting multiple formats and targets.

    Usage:
        exporter = SIEMExporter(formats=["cef", "json"], targets=["file", "syslog"])
        exporter.export(compliance_event_dict)

    Formats: cef, leef, json, syslog
    Targets: file, syslog, nats
    """

    formats: list[str] = field(default_factory=lambda: ["cef", "json"])
    targets: list[str] = field(default_factory=lambda: ["file"])
    log_dir: Path = DEFAULT_SIEM_LOG_DIR
    syslog_host: str = DEFAULT_SYSLOG_HOST
    syslog_port: int = DEFAULT_SYSLOG_PORT
    syslog_proto: Literal["udp", "tcp"] = "udp"

    # Syslog socket (lazy init)
    _syslog_sock: socket.socket | None = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        if "file" in self.targets:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(self, raw_event: dict[str, Any]) -> list[str]:
        """
        Export a Neotron compliance event to all configured targets.

        Returns list of formatted strings that were exported.
        """
        event = SIEMEvent.from_compliance_event(raw_event)
        outputs: list[str] = []

        for fmt in self.formats:
            formatted = self._format(event, fmt)
            outputs.append(formatted)

            for target in self.targets:
                try:
                    self._send(formatted, fmt, target, event)
                except Exception as exc:
                    logger.warning(
                        "SIEM export failed: format=%s target=%s error=%s",
                        fmt,
                        target,
                        exc,
                    )

        return outputs

    def export_batch(self, raw_events: list[dict[str, Any]]) -> int:
        """
        Export multiple events. Returns count of events exported.
        """
        count = 0
        for raw in raw_events:
            self.export(raw)
            count += 1
        return count

    # ------------------------------------------------------------------
    # Formatters (class-level, not instance field)
    # ------------------------------------------------------------------

    FORMATTERS: dict[str, Callable[[SIEMEvent], str]] = field(
        default_factory=lambda: {
            "cef": format_cef,
            "leef": format_leef,
            "json": format_json,
            "syslog": format_syslog_rfc5424,
        },
        init=False,
    )

    def _format(self, event: SIEMEvent, fmt: str) -> str:
        formatter = self.FORMATTERS.get(fmt)
        if formatter is None:
            raise ValueError(f"Unknown SIEM format: {fmt}. Use: {list(self.FORMATTERS)}")
        return formatter(event)

    # ------------------------------------------------------------------
    # Transports
    # ------------------------------------------------------------------

    def _send(self, formatted: str, fmt: str, target: str, event: SIEMEvent) -> None:
        if target == "file":
            self._send_file(formatted, fmt, event)
        elif target == "syslog":
            self._send_syslog(formatted)
        elif target == "nats":
            self._send_nats_sync(formatted, event)
        else:
            raise ValueError(f"Unknown SIEM target: {target}. Use: file, syslog, nats")

    # ------------------------------------------------------------------
    # File transport
    # ------------------------------------------------------------------

    def _send_file(self, formatted: str, fmt: str, event: SIEMEvent) -> None:
        """
        Append formatted event to a rotating log file.

        File naming: {log_dir}/neotron-{format}-{YYYY-MM-DD}.log

        These files are picked up by:
          - Wazuh agent (localfile → syslog)
          - Filebeat (log input → Elasticsearch)
          - Fluentd (tail input → any output)
          - Vector (file source → Loki/OpenSearch)
        """
        date_str = time.strftime("%Y-%m-%d")
        filepath = self.log_dir / f"neotron-{fmt}-{date_str}.log"

        with open(filepath, "a") as f:
            f.write(formatted + "\n")

        # Also write a structured JSON line for Vector (always JSON format)
        if fmt != "json":
            json_path = self.log_dir / f"neotron-json-{date_str}.log"
            with open(json_path, "a") as f:
                f.write(format_json(event) + "\n")

        logger.debug("SIEM event written to %s (%s)", filepath, fmt)

    # ------------------------------------------------------------------
    # Syslog transport (UDP/TCP)
    # ------------------------------------------------------------------

    def _send_syslog(self, formatted: str) -> None:
        """
        Send formatted message to syslog collector via UDP or TCP.

        Uses RFC 5424 syslog format. The message should already be
        formatted by format_syslog_rfc5424().
        """
        if self._syslog_sock is None:
            if self.syslog_proto == "udp":
                self._syslog_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            else:
                self._syslog_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._syslog_sock.settimeout(5.0)
                self._syslog_sock.connect((self.syslog_host, self.syslog_port))

        data = formatted.encode("utf-8") + b"\n"

        if self.syslog_proto == "udp":
            self._syslog_sock.sendto(data, (self.syslog_host, self.syslog_port))
        else:
            self._syslog_sock.sendall(data)

        logger.debug(
            "SIEM event sent to syslog %s:%d/%s",
            self.syslog_host,
            self.syslog_port,
            self.syslog_proto,
        )

    # ------------------------------------------------------------------
    # NATS transport (sync wrapper)
    # ------------------------------------------------------------------

    def _send_nats_sync(self, formatted: str, event: SIEMEvent) -> None:
        """
        Publish to NATS synchronously (fire-and-forget).

        Uses the existing compliance.events infrastructure.
        For async use, call export_to_nats() directly.
        """
        try:
            from neutron.compliance.events import publish_sync

            payload = (
                json.loads(formatted)
                if event.nats_subject
                else {
                    "format": "siem-json",
                    "event": json.loads(formatted) if formatted.startswith("{") else formatted,
                    "timestamp": event.timestamp,
                    "subject": NATS_SIEM_SUBJECT,
                }
            )
            subject = event.nats_subject or NATS_SIEM_SUBJECT
            publish_sync(subject, payload if isinstance(payload, dict) else {"raw": formatted})
        except ImportError:
            logger.warning("NATS export unavailable: compliance.events not importable")
        except Exception as exc:
            logger.warning("NATS publish failed: %s", exc)

    def close(self) -> None:
        """Close syslog socket if open."""
        if self._syslog_sock:
            try:
                self._syslog_sock.close()
            except Exception:
                pass
            self._syslog_sock = None


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def export_to_file(
    event: dict[str, Any],
    log_dir: Path | None = None,
    formats: list[str] | None = None,
) -> list[str]:
    """Quick export a compliance event to SIEM log files."""
    exporter = SIEMExporter(
        formats=formats or ["cef", "json"],
        targets=["file"],
        log_dir=log_dir or DEFAULT_SIEM_LOG_DIR,
    )
    return exporter.export(event)


async def export_to_nats(event: dict[str, Any]) -> None:
    """Quick export a compliance event to NATS (Owasaka SIEM)."""
    from neutron.compliance.events import publish

    siem_event = SIEMEvent.from_compliance_event(event)
    payload = {
        "format": "siem-json",
        "event": json.loads(format_json(siem_event)),
        "subject": NATS_SIEM_SUBJECT,
    }
    await publish(NATS_SIEM_SUBJECT, payload)


def export_to_syslog(
    event: dict[str, Any],
    host: str = DEFAULT_SYSLOG_HOST,
    port: int = DEFAULT_SYSLOG_PORT,
    proto: Literal["udp", "tcp"] = "udp",
) -> str:
    """Quick export a compliance event to syslog."""
    exporter = SIEMExporter(
        formats=["syslog"],
        targets=["syslog"],
        syslog_host=host,
        syslog_port=port,
        syslog_proto=proto,
    )
    outputs = exporter.export(event)
    exporter.close()
    return outputs[0] if outputs else ""


def replay_audit_log(
    log_dir: Path | None = None,
    formats: list[str] | None = None,
    targets: list[str] | None = None,
) -> int:
    """
    Replay all in-memory audit log events through the SIEM exporter.

    Returns count of events exported.
    """
    from neutron.compliance.audit_logger import AuditLogger

    audit = AuditLogger()
    events = audit.get_all()

    exporter = SIEMExporter(
        formats=formats or ["cef", "json"],
        targets=targets or ["file"],
        log_dir=log_dir or DEFAULT_SIEM_LOG_DIR,
    )

    count = exporter.export_batch(events)
    logger.info("Replayed %d audit events to SIEM", count)
    return count
