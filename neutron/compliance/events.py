"""
Compliance event publisher — structured JSON over NATS.

Todos os eventos de compliance (SENTINEL + BASTION + Cortex) são publicados
como JSON estruturado no bus NATS, consumível por:
  - Owasaka (SIEM correlation + alerting)
  - Vector (log shipping → Loki/OpenSearch)
  - adr-ledger (imutabilidade — via neotron.compliance.bastion.v1)
  - Prometheus (métricas via push gateway ou scrape)

Subjects:
  neotron.compliance.sentinel.v1   — guardrail application-layer results
  neotron.compliance.bastion.v1    — kernel-level enforcement events
  neotron.cortex.consensus.v1      — swarm consensus decisions
  neotron.compliance.violation.v1  — bloqueios (severity=block + passed=False)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("neutron.compliance.events")

NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")

# Lazy singleton — só conecta se NATS_URL estiver definido
_nc: Any = None
_nc_ready: bool = False


async def _get_nc():
    """Return a connected NATS client, or None if NATS is unavailable."""
    global _nc, _nc_ready
    if _nc_ready:
        return _nc
    try:
        import nats  # type: ignore

        _nc = await nats.connect(NATS_URL)
        _nc_ready = True
        logger.info("neotron compliance events: NATS conectado em %s", NATS_URL)
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "neotron compliance events: NATS indisponível (%s) — publicação desactivada",
            exc,
        )
        _nc = None
        _nc_ready = True  # não tentar de novo nesta sessão
    return _nc


async def publish(subject: str, payload: dict[str, Any]) -> None:
    """
    Publica *payload* como JSON no *subject* NATS.

    Sempre loga via `logging` (para Vector/stdout JSON) mesmo se NATS falhar.
    Nunca lança excepção — compliance logging é best-effort no transporte
    mas SEMPRE regista localmente.
    """
    payload.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    payload.setdefault("source", "neotron")
    payload.setdefault("subject", subject)

    # 1. Structured JSON log — ingerido pelo Vector → Loki
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))

    # 2. NATS publish — ingerido pelo Owasaka / Phantom / adr-ledger
    nc = await _get_nc()
    if nc is not None:
        try:
            await nc.publish(subject, json.dumps(payload, default=str).encode())
        except Exception as exc:
            logger.warning("NATS publish failed for %s: %s", subject, exc)


def publish_sync(subject: str, payload: dict[str, Any]) -> None:
    """
    Versão síncrona para contextos sem event loop (ex: seccomp enforce).

    Só faz o log JSON — sem NATS (requer asyncio).
    """
    payload.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    payload.setdefault("source", "neotron")
    payload.setdefault("subject", subject)
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))
