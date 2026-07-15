"""
NATS Bridge — Neotron ↔ SPECTRE Event Bus.

Provides a unified NATS client wrapper for publishing and subscribing
to typed compliance events across the NEXUS ecosystem.

Architecture:
  Neotron (Python)                        SPECTRE (Rust)
  ─────────────                           ──────────────
  neutron/events/__init__.py              spectre-events
       │                                        │
       ├─ publish(subject, payload) ──────────► │ (NATS subscriber)
       │                                        │
       ├─ subscribe(subject, callback) ◄────── │ (NATS publisher)
       │                                        │
       └─ request(subject, payload) ◄─────────►│ (request-reply)

Subjects (standardized):
  neotron.compliance.sentinel.v1    — SENTINEL guardrail results
  neotron.compliance.bastion.v1     — BASTION kernel enforcement
  neotron.cortex.consensus.v1       — CORTEX swarm decisions
  neotron.compliance.violation.v1   — blocked violations
  neotron.siem.export.v1            — SIEM export events
  neotron.license.verify.v1         — License verification requests
  spectre.events.*                  — SPECTRE-originated events
  ipguard.results.*                 — IP Guard verification results

Configuration:
  NATS_URL                NATS server URL (default: nats://localhost:4222)
  NATS_TOKEN              Authentication token (optional, legacy)
  NATS_NKEY_SEED          NKey seed string for zero-trust auth (preferred over token)
  NATS_CREDENTIALS_FILE   Path to .creds file (highest priority auth method)
  NATS_NAMESPACE          Subject prefix namespace (default: "")

Auth priority (highest → lowest):
  1. NATS_CREDENTIALS_FILE (.creds file — user + signing key)
  2. NATS_NKEY_SEED        (NKey seed — cryptographic zero-trust)
  3. NATS_TOKEN            (static token — legacy/dev only)
  4. (none)               (unauthenticated — local dev only)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("neutron.events")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_TOKEN = os.environ.get("NATS_TOKEN", "")
NATS_NKEY_SEED = os.environ.get("NATS_NKEY_SEED", "")
NATS_CREDENTIALS_FILE = os.environ.get("NATS_CREDENTIALS_FILE", "")
NATS_NAMESPACE = os.environ.get("NATS_NAMESPACE", "")
NATS_MAX_RECONNECT_ATTEMPTS = int(os.environ.get("NATS_MAX_RECONNECT_ATTEMPTS", "10"))
NATS_RECONNECT_WAIT = float(os.environ.get("NATS_RECONNECT_WAIT", "2.0"))


def _ns(subject: str) -> str:
    """Prefix subject with namespace if configured."""
    if NATS_NAMESPACE:
        return f"{NATS_NAMESPACE}.{subject}"
    return subject


# ---------------------------------------------------------------------------
# Connection (async — primary)
# ---------------------------------------------------------------------------

_nc: Any = None
_nc_ready: bool = False
_nc_lock = threading.Lock()


async def get_connection() -> Any | None:
    """
    Return a connected NATS client, or None if NATS is unavailable.

    Uses lazy connection — only connects on first use. Idempotent.
    Reconnection is handled by nats-py's built-in reconnect loop.
    """
    global _nc, _nc_ready

    if _nc_ready:
        return _nc

    with _nc_lock:
        if _nc_ready:  # double-check
            return _nc

        try:
            import nats  # type: ignore[import-untyped]

            options: dict[str, Any] = {
                "max_reconnect_attempts": NATS_MAX_RECONNECT_ATTEMPTS,
                "reconnect_time_wait": NATS_RECONNECT_WAIT,
            }

            # Auth priority: credentials file > NKey seed > token > unauthenticated
            if NATS_CREDENTIALS_FILE:
                options["credentials"] = NATS_CREDENTIALS_FILE
                logger.info("NATS auth: credentials file (%s)", NATS_CREDENTIALS_FILE)
            elif NATS_NKEY_SEED:
                try:
                    import nkeys  # type: ignore[import-untyped]

                    kp = nkeys.from_seed(NATS_NKEY_SEED.encode())
                    options["nkeys_seed"] = NATS_NKEY_SEED
                    logger.info("NATS auth: NKey (public=%s)", kp.public_key.decode()[:8] + "…")
                except ImportError:
                    logger.warning(
                        "NATS_NKEY_SEED set but 'nkeys' package not installed — "
                        "falling back to token auth. Install: uv add nkeys"
                    )
                    if NATS_TOKEN:
                        options["token"] = NATS_TOKEN
            elif NATS_TOKEN:
                options["token"] = NATS_TOKEN
                logger.info("NATS auth: static token (legacy)")
            else:
                logger.info("NATS auth: unauthenticated (dev mode)")

            _nc = await nats.connect(NATS_URL, **options)
            _nc_ready = True
            logger.info("NATS bridge connected: %s", NATS_URL)
        except ImportError:
            logger.warning(
                "nats-py not installed — NATS bridge disabled. Install with: uv add nats-py"
            )
            _nc = None
            _nc_ready = True
        except Exception as exc:
            logger.warning("NATS bridge unavailable (%s) — event bus disabled", exc)
            _nc = None
            _nc_ready = True

    return _nc


async def close_connection() -> None:
    """Close the NATS connection (for graceful shutdown)."""
    global _nc, _nc_ready
    if _nc is not None:
        try:
            await _nc.close()
            logger.info("NATS bridge disconnected")
        except Exception as exc:
            logger.debug("NATS close error: %s", exc)
    _nc = None
    _nc_ready = False


# ---------------------------------------------------------------------------
# Publish (fire-and-forget)
# ---------------------------------------------------------------------------


async def publish(
    subject: str, payload: dict[str, Any], headers: dict[str, str] | None = None
) -> bool:
    """
    Publish a JSON payload to a NATS subject.

    Returns True if published, False if NATS is unavailable.
    Never raises — compliance events must not block the pipeline.

    Args:
        subject: NATS subject (will be namespace-prefixed if configured)
        payload: JSON-serializable dict
        headers: Optional NATS headers (key-value pairs)

    Example:
        await publish("neotron.compliance.sentinel.v1", {
            "audit_id": 42,
            "guardrail_name": "lgpd_consent",
            "passed": True,
            "severity": "info",
        })
    """
    nc = await get_connection()
    if nc is None:
        return False

    try:
        data = json.dumps(payload, default=str).encode()
        await nc.publish(_ns(subject), data)
        logger.debug("NATS published → %s", subject)
        return True
    except Exception as exc:
        logger.warning("NATS publish failed for %s: %s", subject, exc)
        return False


# ---------------------------------------------------------------------------
# Subscribe (async callback)
# ---------------------------------------------------------------------------


async def subscribe(
    subject: str,
    callback: Callable[[dict[str, Any]], Any],
    queue_group: str | None = None,
) -> Any | None:
    """
    Subscribe to a NATS subject with an async callback.

    Args:
        subject: NATS subject (supports wildcards: *, >)
        callback: Async callable receiving the decoded JSON payload
        queue_group: Optional queue group for load-balanced delivery

    Returns:
        nats.js.JetStream.PullSubscription or nats.Subscription, or None if unavailable

    Example:
        async def on_sentinel(msg):
            event = json.loads(msg.data)
            print(f"SENTINEL event: {event}")

        await subscribe("neotron.compliance.sentinel.v1", on_sentinel, "workers")
    """
    nc = await get_connection()
    if nc is None:
        return None

    async def _wrapper(msg: Any) -> None:
        """Decode JSON and call the user callback."""
        try:
            payload = json.loads(msg.data)
            await callback(payload)
        except json.JSONDecodeError:
            logger.warning("NATS message on %s is not valid JSON", subject)
        except Exception as exc:
            logger.warning("NATS callback error on %s: %s", subject, exc)

    try:
        if queue_group:
            sub = await nc.subscribe(_ns(subject), cb=_wrapper, queue=queue_group)
        else:
            sub = await nc.subscribe(_ns(subject), cb=_wrapper)

        logger.info("NATS subscribed → %s (queue=%s)", subject, queue_group or "none")
        return sub
    except Exception as exc:
        logger.warning("NATS subscribe failed for %s: %s", subject, exc)
        return None


# ---------------------------------------------------------------------------
# Request-Reply
# ---------------------------------------------------------------------------


async def request(
    subject: str,
    payload: dict[str, Any],
    timeout: float = 5.0,
) -> dict[str, Any] | None:
    """
    Send a request and wait for a reply (NATS request-reply pattern).

    Used for synchronous cross-service communication:
      Neotron → SPECTRE, Neotron → IP Guard, etc.

    Args:
        subject: NATS subject to send the request to
        payload: JSON-serializable request body
        timeout: Maximum wait time in seconds

    Returns:
        Decoded JSON response dict, or None if no reply / unavailable

    Example:
        result = await request("ipguard.license.verify", {
            "flake_path": "/path/to/flake.nix",
            "package": "python3",
        })
        if result:
            print(f"License NFT: {result['token_id']}")
    """
    nc = await get_connection()
    if nc is None:
        return None

    try:
        data = json.dumps(payload, default=str).encode()
        reply = await nc.request(_ns(subject), data, timeout=timeout)
        return json.loads(reply.data)
    except TimeoutError:
        logger.warning("NATS request timed out for %s (%.1fs)", subject, timeout)
        return None
    except Exception as exc:
        logger.warning("NATS request failed for %s: %s", subject, exc)
        return None


# ---------------------------------------------------------------------------
# JetStream (persistent streams)
# ---------------------------------------------------------------------------


async def get_jetstream() -> Any | None:
    """
    Return a JetStream context, or None if unavailable.

    JetStream enables persistent, replayable event streams
    for audit trails and compliance archiving.
    """
    nc = await get_connection()
    if nc is None:
        return None

    try:
        import nats.js  # type: ignore[import-untyped]

        return nc.jetstream()
    except ImportError:
        logger.warning("nats-py JetStream not available — upgrade nats-py")
        return None
    except Exception as exc:
        logger.warning("JetStream unavailable: %s", exc)
        return None


async def publish_jetstream(
    stream: str,
    subject: str,
    payload: dict[str, Any],
) -> bool:
    """
    Publish to a JetStream stream for persistent, replayable storage.

    Args:
        stream: JetStream stream name
        subject: Subject within the stream
        payload: JSON-serializable dict

    Returns:
        True if published and acknowledged, False otherwise
    """
    js = await get_jetstream()
    if js is None:
        return False

    try:
        data = json.dumps(payload, default=str).encode()
        ack = await js.publish(_ns(subject), data)
        logger.debug("JetStream published → %s/%s (seq=%s)", stream, subject, ack.seq)
        return True
    except Exception as exc:
        logger.warning("JetStream publish failed for %s/%s: %s", stream, subject, exc)
        return False


# ---------------------------------------------------------------------------
# Channel — high-level typed publisher (mirrors Go channels)
# ---------------------------------------------------------------------------


class EventChannel:
    """
    Typed event channel for publishing to a specific NATS subject.

    Provides a Go-like channel interface:
        channel = EventChannel("neotron.compliance.sentinel.v1")
        await channel.send({"audit_id": 42, "passed": True})

    Also provides a sync version for non-async contexts.
    """

    def __init__(self, subject: str, queue: str | None = None):
        self.subject = subject
        self.queue = queue

    async def send(self, payload: dict[str, Any]) -> bool:
        """Publish a message on this channel (async)."""
        return await publish(self.subject, payload)

    def send_sync(self, payload: dict[str, Any]) -> bool:
        """Publish a message on this channel (sync, fire-and-forget)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return asyncio.ensure_future(self.send(payload)) is not None
        except RuntimeError:
            pass
        return False

    async def recv(self, callback: Callable[[dict[str, Any]], Any]) -> Any | None:
        """Subscribe to this channel with a callback."""
        return await subscribe(self.subject, callback, self.queue)

    def __repr__(self) -> str:
        return f"EventChannel({self.subject!r})"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def health() -> dict[str, Any]:
    """
    Check NATS bridge health.

    Returns a dict with connection status and server info.
    """
    nc = await get_connection()
    if nc is None:
        return {
            "status": "unavailable",
            "nats_url": NATS_URL,
            "connected": False,
        }

    try:
        auth_method = (
            "credentials_file"
            if NATS_CREDENTIALS_FILE
            else "nkey" if NATS_NKEY_SEED else "token" if NATS_TOKEN else "none"
        )
        return {
            "status": "healthy",
            "nats_url": NATS_URL,
            "connected": nc.is_connected,
            "auth_method": auth_method,
            "server_info": nc.server_info if hasattr(nc, "server_info") else {},
            "namespace": NATS_NAMESPACE or "(none)",
        }
    except Exception:
        return {
            "status": "degraded",
            "nats_url": NATS_URL,
            "connected": False,
        }


# ---------------------------------------------------------------------------
# Event helpers — standard event types
# ---------------------------------------------------------------------------


async def emit_sentinel(payload: dict[str, Any]) -> bool:
    """Emit a SENTINEL (Layer 1) compliance event."""
    return await publish("neotron.compliance.sentinel.v1", payload)


async def emit_bastion(payload: dict[str, Any]) -> bool:
    """Emit a BASTION (Layer 2) kernel enforcement event."""
    return await publish("neotron.compliance.bastion.v1", payload)


async def emit_cortex(payload: dict[str, Any]) -> bool:
    """Emit a CORTEX (Layer 3) swarm consensus event."""
    return await publish("neotron.cortex.consensus.v1", payload)


async def emit_violation(payload: dict[str, Any]) -> bool:
    """Emit a compliance violation (block/critical/high severity)."""
    return await publish("neotron.compliance.violation.v1", payload)


async def emit_siem(payload: dict[str, Any]) -> bool:
    """Emit a SIEM export event."""
    return await publish("neotron.siem.export.v1", payload)


# ---------------------------------------------------------------------------
# Pre-built channels for standard event types
# ---------------------------------------------------------------------------

sentinel_channel = EventChannel("neotron.compliance.sentinel.v1")
bastion_channel = EventChannel("neotron.compliance.bastion.v1")
cortex_channel = EventChannel("neotron.cortex.consensus.v1")
violation_channel = EventChannel("neotron.compliance.violation.v1")
siem_channel = EventChannel("neotron.siem.export.v1")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Connection
    "get_connection",
    "close_connection",
    # Publish / Subscribe
    "publish",
    "subscribe",
    "request",
    # JetStream
    "get_jetstream",
    "publish_jetstream",
    # Channel
    "EventChannel",
    # Health
    "health",
    # Emit helpers
    "emit_sentinel",
    "emit_bastion",
    "emit_cortex",
    "emit_violation",
    "emit_siem",
    # Pre-built channels
    "sentinel_channel",
    "bastion_channel",
    "cortex_channel",
    "violation_channel",
    "siem_channel",
    # Config
    "NATS_URL",
    "NATS_NKEY_SEED",
    "NATS_CREDENTIALS_FILE",
]
