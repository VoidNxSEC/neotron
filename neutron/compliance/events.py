"""
Compliance event publisher — structured JSON over NATS (or SPECTRE Proxy).

Todos os eventos de compliance (SENTINEL + BASTION + Cortex) são publicados
como JSON estruturado. Dois modos de transporte:

  1. NATS direto (default): Neotron → NATS → Owasaka SIEM
  2. SPECTRE Proxy (SPECTRE_PROXY_URL definida):
     Neotron → spectre-proxy (JWT auth + rate limit + circuit breaker) → NATS → Owasaka

Consumidores:
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
    Publica *payload* como JSON no *subject* NATS (ou via SPECTRE Proxy).

    Sempre loga via `logging` (para Vector/stdout JSON) mesmo se transporte falhar.
    Nunca lança excepção — compliance logging é best-effort no transporte
    mas SEMPRE regista localmente.

    Se SPECTRE_PROXY_URL estiver definida, publica via spectre-proxy
    (que adiciona JWT auth, rate limit, circuit breaker, typed schemas).
    Caso contrário, publica diretamente no NATS.
    """
    payload.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    payload.setdefault("source", "neotron")
    payload.setdefault("subject", subject)

    # 1. Structured JSON log — ingerido pelo Vector → Loki
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))

    # 2. SPECTRE Proxy (preferred) or NATS (fallback)
    if os.environ.get("SPECTRE_PROXY_URL"):
        _publish_via_spectre(subject, payload)
        return

    # 3. NATS publish — ingerido pelo Owasaka / Phantom / adr-ledger
    nc = await _get_nc()
    if nc is not None:
        try:
            await nc.publish(subject, json.dumps(payload, default=str).encode())
        except Exception as exc:
            logger.warning("NATS publish failed for %s: %s", subject, exc)


def publish_sync(subject: str, payload: dict[str, Any]) -> None:
    """
    Versão síncrona para contextos sem event loop (ex: seccomp enforce).

    Sempre loga JSON localmente. Se SPECTRE_PROXY_URL estiver definida,
    publica via SPECTRE Proxy (HTTP, síncrono). Caso contrário, só loga.
    """
    payload.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    payload.setdefault("source", "neotron")
    payload.setdefault("subject", subject)
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))

    # SPECTRE Proxy — sync HTTP (works without event loop)
    if os.environ.get("SPECTRE_PROXY_URL"):
        _publish_via_spectre(subject, payload)


def _publish_via_spectre(subject: str, payload: dict[str, Any]) -> None:
    """
    Publish a compliance event through the SPECTRE Proxy.

    Uses the global SpectreProxyClient singleton. Auto-routes to the
    correct compliance endpoint based on subject and event fields.

    Best-effort — never raises. Logs success or failure.
    """
    try:
        from neutron.spectre import get_spectre_client

        client = get_spectre_client()
        result = client.publish(payload)
        logger.debug("SPECTRE proxy published: %s", result.get("event_id", "unknown"))
    except Exception as exc:
        logger.warning("SPECTRE proxy publish failed for %s: %s", subject, exc)
