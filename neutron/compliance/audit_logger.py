"""
Audit Logger - Immutable audit trail for compliance events

Simple in-memory audit logger for compliance validation events.
In production, this would write to PostgreSQL with append-only constraints.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("neutron.compliance.audit_logger")


class AuditLogger:
    """
    Simple audit logger for compliance events

    In-memory implementation for development.
    Production should use PostgreSQL with append-only table.
    """

    _instance = None
    _audit_log: list[Dict[str, Any]] = []
    _counter = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def log(self, event: Dict[str, Any]) -> int:
        """
        Log compliance event to audit trail

        Args:
            event: Event data to log

        Returns:
            Audit ID (integer)
        """
        self._counter += 1
        audit_id = self._counter

        audit_entry = {
            "audit_id": audit_id,
            "timestamp": datetime.utcnow().isoformat(),
            **event
        }

        self._audit_log.append(audit_entry)

        logger.debug(f"Audit event logged: ID={audit_id}")

        return audit_id

    def get_all(self) -> list[Dict[str, Any]]:
        """Get all audit log entries"""
        return self._audit_log.copy()

    def clear(self):
        """Clear audit log (for testing only)"""
        self._audit_log.clear()
        self._counter = 0
        logger.warning("Audit log cleared (testing only!)")
