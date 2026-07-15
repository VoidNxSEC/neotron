"""
SPECTRE Proxy Client — Neotron → SPECTRE Fleet Integration.

Routes all Neotron compliance events through the SPECTRE AI Management Plane
instead of publishing directly to NATS. This gives us:

  - JWT authentication on every request
  - Rate limiting + circuit breaking (proxy-side + client-side)
  - Typed event schemas (Rust spectre-events)
  - Audit trail: Neotron → spectre-proxy → NATS → Owasaka SIEM

Architecture:
  Neotron (Python)
    │
    ├─── neutron/spectre/client.py   ← this module
    │    POST /api/v1/compliance/sentinel
    │    POST /api/v1/compliance/bastion
    │    POST /api/v1/compliance/violation
    │    ...
    │
    ▼
  spectre-proxy (Rust) :8080
    │  JWT auth → Rate limit → Circuit breaker → NATS
    │
    ▼
  NATS → Owasaka SIEM (Go)
"""

from neutron.spectre.client import SpectreProxyClient, SpectreProxyConfig, get_spectre_client

__all__ = [
    "SpectreProxyClient",
    "SpectreProxyConfig",
    "get_spectre_client",
]
