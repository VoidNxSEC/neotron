"""
Audit Logger — immutable compliance audit trail com JSON estruturado.

Emite cada evento em dois canais:
  1. `logging` (JSON para stdout/stderr) — ingerido pelo Vector → Loki/OpenSearch
  2. NATS `neotron.compliance.sentinel.v1` — consumido por Owasaka SIEM

Em produção: PG append-only (já documentado nos ADRs).
Em desenvolvimento: in-memory + JSON log.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from neutron.compliance.events import publish_sync

# Logger dedicado — Vector filtra por nome para routing
_audit_logger = logging.getLogger("neutron.audit")


class AuditLogger:
    """
    Singleton audit logger para eventos de compliance.

    Cada evento é:
      - Registado como JSON estruturado via `logging` (Vector → Loki)
      - Publicado em NATS (Owasaka SIEM)
      - Mantido em memória para queries in-process (testing)

    Formato JSON de cada entrada:
    {
        "audit_id": 1,
        "timestamp": "2026-04-07T...",
        "guardrail_name": "lgpd_art18_explanation",
        "regulation": "LGPD",
        "agent_output_hash": "sha256:...",
        "validation_result": { "passed": true, "details": "...", "confidence": 0.9 },
        "severity": "block",
        "passed": true,
        "source": "neotron",
        "subject": "neotron.compliance.sentinel.v1"
    }
    """

    _instance: AuditLogger | None = None
    _audit_log: list[dict[str, Any]] = []
    _counter: int = 0

    def __new__(cls) -> AuditLogger:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def log(self, event: dict[str, Any]) -> int:
        """
        Regista evento de compliance.

        Args:
            event: dados do evento (guardrail, resultado, hash do output)

        Returns:
            audit_id único (int)
        """
        self._counter += 1
        audit_id = self._counter

        entry: dict[str, Any] = {
            "audit_id": audit_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "neotron",
            "subject": "neotron.compliance.sentinel.v1",
            **event,
        }

        self._audit_log.append(entry)

        # 1. JSON estruturado via logging (Vector lê isto)
        _audit_logger.info(json.dumps(entry, ensure_ascii=False, default=str))

        # 2. NATS (síncrono — sem event loop neste ponto)
        publish_sync("neotron.compliance.sentinel.v1", entry)

        return audit_id

    def get_all(self) -> list[dict[str, Any]]:
        """Retorna todos os eventos (cópia)."""
        return list(self._audit_log)

    def get_violations(self) -> list[dict[str, Any]]:
        """Retorna só os eventos falhados (passed=False)."""
        return [e for e in self._audit_log if not e.get("passed", True)]

    def clear(self) -> None:
        """Limpa o log — apenas para testes."""
        self._audit_log.clear()
        self._counter = 0
        _audit_logger.warning(json.dumps({"event": "audit_log_cleared", "source": "neotron"}))
