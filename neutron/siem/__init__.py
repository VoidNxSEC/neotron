"""
SIEM Exporter — Structured log export for Security Information & Event Management.

Pipelines:
  Neotron → CEF/Syslog → File → Filebeat/Wazuh → SIEM
  Neotron → JSON → NATS → Owasaka SIEM (existing)
  Neotron → Syslog UDP → Splunk / QRadar / ArcSight (direct)

Supported formats:
  - CEF (Common Event Format) — ArcSight, Splunk, QRadar
  - LEEF (Log Event Extended Format) — IBM QRadar
  - JSON (structured) — Elasticsearch, Owasaka, custom SIEMs
  - Syslog RFC 5424 — Standard syslog

Export targets:
  - File (for agent pickup: Wazuh, Filebeat, Fluentd)
  - Syslog UDP/TCP (direct to SIEM collector)
  - NATS (to Owasaka SIEM — existing compliance.events pipeline)
"""

from neutron.siem.exporters import (
    SIEMExporter,
    export_to_file,
    export_to_nats,
    export_to_syslog,
)
from neutron.siem.formatters import (
    SIEMEvent,
    format_cef,
    format_json,
    format_leef,
    format_syslog_rfc5424,
)

__all__ = [
    # Formatters
    "SIEMEvent",
    "format_cef",
    "format_leef",
    "format_json",
    "format_syslog_rfc5424",
    # Exporters
    "SIEMExporter",
    "export_to_file",
    "export_to_syslog",
    "export_to_nats",
]
