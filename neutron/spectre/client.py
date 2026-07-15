"""
SPECTRE Proxy HTTP Client — Neotron → spectre-proxy gateway.

Usage:
    from neutron.spectre import get_spectre_client

    client = get_spectre_client()
    client.publish_sentinel(event_dict)
    client.publish_violation(event_dict)
    client.publish_batch([event1, event2, event3])

Environment variables:
    SPECTRE_PROXY_URL      Base URL (default: http://localhost:8080)
    SPECTRE_JWT_SECRET     Shared secret for JWT signing (default: "neotron-secret")
    SPECTRE_SERVICE_ID     Service identity in JWT claims (default: "neotron")
    SPECTRE_DISABLED       Set to "1" to bypass proxy (publish directly to NATS)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger("neutron.spectre.client")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class SpectreProxyConfig:
    """Configuration for SPECTRE proxy client."""

    base_url: str = os.environ.get("SPECTRE_PROXY_URL", "http://localhost:8080")
    jwt_secret: str = os.environ.get("SPECTRE_JWT_SECRET", "neotron-secret")
    service_id: str = os.environ.get("SPECTRE_SERVICE_ID", "neotron")
    disabled: bool = os.environ.get("SPECTRE_DISABLED", "") == "1"
    timeout_seconds: float = float(os.environ.get("SPECTRE_TIMEOUT", "5.0"))
    max_retries: int = int(os.environ.get("SPECTRE_MAX_RETRIES", "3"))


# ---------------------------------------------------------------------------
# Simple JWT (HS256) — avoids pyjwt dependency
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _create_jwt(service_id: str, secret: str) -> str:
    """
    Create a simple HS256 JWT for spectre-proxy authentication.

    Token format:
      header.payload.signature

    Header:  {"alg":"HS256","typ":"JWT"}
    Payload: {"sub":"<service_id>","role":"neotron-agent","iat":<ts>,"exp":<ts+3600>}
    """
    now = int(time.time())
    header = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload = _b64url_encode(
        json.dumps(
            {
                "sub": service_id,
                "role": "neotron-agent",
                "iat": now,
                "exp": now + 3600,  # 1 hour
            },
            separators=(",", ":"),
        ).encode()
    )

    signing_input = f"{header}.{payload}"
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    signature = _b64url_encode(sig)

    return f"{signing_input}.{signature}"


# ---------------------------------------------------------------------------
# Circuit Breaker (client-side)
# ---------------------------------------------------------------------------


@dataclass
class ClientCircuitBreaker:
    """
    Client-side circuit breaker for spectre-proxy calls.

    Opens after `failure_threshold` consecutive failures and
    stays open for `reset_timeout` seconds before testing recovery.
    """

    failure_threshold: int = 5
    reset_timeout: float = 30.0
    _failure_count: int = field(default=0, init=False)
    _last_failure: float = field(default=0.0, init=False)
    _state: Literal["closed", "open", "half_open"] = field(default="closed", init=False)

    def allow_request(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "open":
            if time.monotonic() - self._last_failure >= self.reset_timeout:
                self._state = "half_open"
                return True
            return False
        # half_open — allow one probe
        return True

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning("SPECTRE circuit breaker OPEN (%d failures)", self._failure_count)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class SpectreProxyClient:
    """
    HTTP client for the SPECTRE Proxy API Gateway.

    Routes Neotron compliance events through spectre-proxy
    which handles JWT auth, rate limiting, circuit breaking,
    and publishing to NATS with typed event schemas.
    """

    def __init__(self, config: SpectreProxyConfig | None = None):
        self.config = config or SpectreProxyConfig()
        self._circuit = ClientCircuitBreaker()
        self._jwt: str | None = None
        self._jwt_created: float = 0.0
        self._session: Any = None  # lazy httpx import

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------

    def _get_jwt(self) -> str:
        """Get or refresh JWT token (valid for 1 hour, refresh at 50 min)."""
        now = time.monotonic()
        if self._jwt is None or (now - self._jwt_created) > 3000:  # 50 min
            self._jwt = _create_jwt(self.config.service_id, self.config.jwt_secret)
            self._jwt_created = now
            logger.debug("SPECTRE JWT refreshed for %s", self.config.service_id)
        return self._jwt

    def _get_session(self):
        """Lazy import httpx to avoid dependency at module load."""
        if self._session is None:
            try:
                import httpx  # type: ignore[import-untyped]

                self._session = httpx.Client(timeout=self.config.timeout_seconds)
            except ImportError:
                logger.warning("httpx not installed — using urllib fallback")
                self._session = False  # sentinel for urllib
        return self._session

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to spectre-proxy with JWT auth and retry logic."""

        if self.config.disabled:
            logger.debug("SPECTRE proxy disabled — skipping %s", path)
            return {"status": "skipped", "reason": "spectre_disabled"}

        url = f"{self.config.base_url}{path}"
        jwt = self._get_jwt()
        headers = {
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
        }
        body = json.dumps(payload, default=str).encode()

        last_error = None
        for attempt in range(self.config.max_retries + 1):
            if not self._circuit.allow_request():
                raise SpectreProxyError("Circuit breaker open — spectre-proxy unavailable")

            try:
                session = self._get_session()
                if session is False:  # urllib fallback
                    return self._post_urllib(url, headers, body)

                resp = session.post(url, content=body, headers=headers)
                data = resp.json()

                if resp.is_success:
                    self._circuit.record_success()
                    return data

                # 4xx — don't retry
                if 400 <= resp.status_code < 500:
                    raise SpectreProxyError(
                        f"SPECTRE proxy returned {resp.status_code}: {data.get('error', 'unknown')}",
                        status_code=resp.status_code,
                    )

                # 5xx — retry
                last_error = SpectreProxyError(
                    f"SPECTRE proxy returned {resp.status_code}",
                    status_code=resp.status_code,
                )

            except SpectreProxyError:
                raise
            except Exception as e:
                last_error = SpectreProxyError(f"SPECTRE proxy unreachable: {e}")

            if attempt < self.config.max_retries:
                wait = 2**attempt * 0.1  # 0.1, 0.2, 0.4s
                logger.warning(
                    "SPECTRE retry %d/%d after %.1fs: %s",
                    attempt + 1,
                    self.config.max_retries,
                    wait,
                    last_error,
                )
                time.sleep(wait)

        self._circuit.record_failure()
        raise last_error or SpectreProxyError("SPECTRE proxy request failed")

    def _post_urllib(self, url: str, headers: dict, body: bytes) -> dict[str, Any]:
        """Fallback HTTP client using urllib (no httpx dependency)."""
        import urllib.error
        import urllib.request

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise SpectreProxyError(
                f"SPECTRE proxy returned {e.code}: {e.reason}",
                status_code=e.code,
            )

    # ------------------------------------------------------------------
    # Compliance API
    # ------------------------------------------------------------------

    def publish_sentinel(self, event: dict[str, Any]) -> dict[str, Any]:
        """Publish a SENTINEL (Layer 1) compliance event."""
        return self._post("/api/v1/compliance/sentinel", self._normalize(event))

    def publish_bastion(self, event: dict[str, Any]) -> dict[str, Any]:
        """Publish a BASTION (Layer 2) kernel enforcement event."""
        return self._post("/api/v1/compliance/bastion", self._normalize(event))

    def publish_cortex(self, event: dict[str, Any]) -> dict[str, Any]:
        """Publish a CORTEX (Layer 3) swarm consensus event."""
        return self._post("/api/v1/compliance/cortex", self._normalize(event))

    def publish_violation(self, event: dict[str, Any]) -> dict[str, Any]:
        """Publish a compliance violation (any layer, severity=block/critical/high)."""
        return self._post("/api/v1/compliance/violation", self._normalize(event))

    def publish_temporal(self, event: dict[str, Any]) -> dict[str, Any]:
        """Publish a TEMPORAL (Layer 0) guard event."""
        return self._post("/api/v1/compliance/temporal", self._normalize(event))

    def publish_siem(self, event: dict[str, Any]) -> dict[str, Any]:
        """Publish a SIEM export event."""
        return self._post("/api/v1/compliance/siem", self._normalize(event))

    def publish_batch(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Publish multiple compliance events in a single batch request."""
        normalized = [self._normalize(e) for e in events]
        return self._post("/api/v1/compliance/batch", {"events": normalized})

    def health(self) -> dict[str, Any]:
        """Check spectre-proxy health."""
        return self._post("/health", {})

    # ------------------------------------------------------------------
    # Auto-route by severity
    # ------------------------------------------------------------------

    def publish(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Auto-route a compliance event to the correct endpoint.

        Decision matrix:
          - passed=false + severity in (block, critical, high) → violation
          - passed=false → sentinel (generic failure)
          - passed=true  → siem (routine audit)

        Also checks guardrail_name for routing hints:
          - guardrail_name starts with "temporal_" → temporal
          - guardrail_name starts with "bastion_"  → bastion
        """
        guardrail = event.get("guardrail_name", "")
        passed = event.get("passed", True)
        severity = event.get("severity", "info")

        # Route by guardrail prefix
        if guardrail.startswith("temporal_"):
            return self.publish_temporal(event)
        if guardrail.startswith("bastion_"):
            return self.publish_bastion(event)
        if guardrail.startswith("cortex_"):
            return self.publish_cortex(event)

        # Route by severity
        if not passed and severity in ("block", "critical", "high"):
            return self.publish_violation(event)
        if not passed:
            return self.publish_sentinel(event)
        return self.publish_siem(event)

    # ------------------------------------------------------------------
    # Normalizer
    # ------------------------------------------------------------------

    def _normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize a Neotron compliance event to the spectre-proxy schema.

        Maps AuditLogger fields → ComplianceEventRequest fields.
        """
        return {
            "audit_id": int(event.get("audit_id", 0)),
            "guardrail_name": str(event.get("guardrail_name", "unknown")),
            "regulation": str(event.get("regulation", "N/A")),
            "severity": str(event.get("severity", "info")),
            "passed": bool(event.get("passed", True)),
            "confidence": float(event.get("confidence", 0.0)),
            "agent_output_hash": str(event.get("agent_output_hash", "")),
            "details": str(event.get("details", "")),
            "agent_id": str(event.get("agent_id", "")),
            "risk_score": float(event.get("risk_score", 0.0)),
            "reputation": float(event.get("reputation", 0.0)),
            "metadata": event.get("metadata", {}),
        }

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session and self._session is not False:
            self._session.close()
            self._session = None

    def __enter__(self) -> SpectreProxyClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class SpectreProxyError(Exception):
    """Error from SPECTRE proxy communication."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_client: SpectreProxyClient | None = None


def get_spectre_client(config: SpectreProxyConfig | None = None) -> SpectreProxyClient:
    """
    Get or create the global SPECTRE proxy client singleton.

    The client is lazily initialized on first call. Use environment
    variables (SPECTRE_PROXY_URL, SPECTRE_JWT_SECRET, etc.) for configuration
    or pass an explicit SpectreProxyConfig.
    """
    global _client
    if _client is None or config is not None:
        _client = SpectreProxyClient(config)
    return _client
