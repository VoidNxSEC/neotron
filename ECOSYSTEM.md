# NEXUS Umbrella — Ecossistema Completo

> **Last updated**: 2026-05-21  
> **Principle**: One document. 5 repositories. Zero drift.  
> **Purpose**: Single source of truth for all cross-repo architecture, data flow, and tooling.

---

## 🗺️ Repository Map

```
/home/kernelcore/master/
│
├── neotron/                  ← NEXUS Platform (Python + Rust)
│   │                           AI Compliance Orchestration
│   ├── neutron/                ✅ CLI (50+ cmds) + BASTION (Landlock) + SENTINEL + CORTEX
│   ├── neutron/siem/           ✅ CEF/JSON/Syslog export (Wazuh, Splunk, Owasaka)
│   ├── neutron/spectre/        ✅ SPECTRE Proxy HTTP client (JWT + circuit breaker)
│   ├── neutron/compliance/     ✅ AuditLogger → NATS or SPECTRE Proxy
│   ├── IP-Guard/               ⚠️  Nix + Blockchain + ZK license compliance (Rust)
│   └── flake.nix               Nix dev shell
│
├── spectre/                  ← SPECTRE Fleet (Rust) — Phase 4
│   │                           AI Management Plane · Event Bus · Zero-Trust Gateway
│   ├── crates/spectre-core/    ✅ Types, errors, config, logging
│   ├── crates/spectre-events/  ✅ 30+ event types, NATS client, pub/sub
│   ├── crates/spectre-proxy/   ✅ JWT+RBAC, rate limit, circuit breaker, OTLP (:3000)
│   ├── crates/spectre-secrets/ ✅ SecretManager (JWT_SECRET, key rotation)
│   ├── crates/spectre-observability/ ✅ OpenTelemetry, Prometheus
│   ├── charts/                 ✅ Helm charts (17 files, Kubernetes)
│   └── nix/                    ✅ NixOS module for NATS
│
├── owasaka/                  ← OWASAKA SIEM (Go)
│   │                           Zero-trust air-gapped SIEM platform
│   ├── internal/events/        ✅ NeotronComplianceSubscriber → NATS → Pipeline
│   ├── internal/models/        ✅ NetworkEvent + EventCompliance type
│   ├── internal/api/           ✅ WebSocket hub + Prometheus
│   └── web/                    ✅ SvelteKit dashboard (D3.js topology)
│
└── arch/phantom-nx/libs/     ← The Arsenal (Rust)
    ├── phantom-soc-kernel/     IntelAgent — AI agent proofs + DAO
    │   ├── core/                 ✅ Agent, Task, QualityGate, Context, Proof
    │   ├── governance/dao/       ⬜ Algorand PyTeal contracts
    │   └── mcp/                  ⬜ MCP server implementations
    │
    └── spectre-rust/           [DEPRECATED — use /master/spectre/ instead]
```

---

## 🌊 Data Flow — The Complete Picture

```
                        USER / CLI
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    NEOTRON (Python :8000)                     │
│                                                              │
│  neotron siem export --format cef                            │
│  neotron security scan                                       │
│  neotron compliance check                                    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              4-Layer Defense-in-Depth                │     │
│  │  Layer 0: TEMPORAL (boiling-frog detection)          │     │
│  │  Layer 1: SENTINEL (LGPD/GDPR guardrails)            │     │
│  │  Layer 2: BASTION (Landlock + seccomp kernel)        │     │
│  │  Layer 3: CORTEX (multi-agent swarm consensus)       │     │
│  │  Layer 4: AUDIT (SIEM export + blockchain trail)    │     │
│  └──────────────────────┬──────────────────────────────┘     │
│                         │                                    │
│  AuditLogger.log() ─────┤                                    │
│  SIEMExporter ──────────┤                                    │
│  SpectreProxyClient ────┘                                    │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ CEF File │ │JSON File │ │ Syslog   │
       │ /siem/   │ │ /siem/   │ │ UDP:514  │
       └────┬─────┘ └────┬─────┘ └────┬─────┘
            │            │            │
            ▼            ▼            ▼
       Wazuh/       Vector/       Splunk/
       Filebeat     Fluentd       QRadar
            │            │            │
            └────────────┼────────────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          ▼          ▼
         ┌──────────────────────────────────────┐
         │       SPECTRE FLEET (Rust :3000)      │
         │         AI Management Plane           │
         │                                       │
         │  POST /api/v1/ingest                  │
         │  POST /api/v1/neutron/*path → Neotron │
         │                                       │
         │  ┌─────────────────────────────────┐  │
         │  │ JWT Auth → RBAC → Rate Limit    │  │
         │  │ → Circuit Breaker → OTLP Trace  │  │
         │  └─────────────┬───────────────────┘  │
         │                │                      │
         │  spectre-events → NATS :4222          │
         └────────────────┼──────────────────────┘
                          │
         ┌────────────────┼──────────────────────┐
         │                │                      │
         ▼                ▼                      ▼
  ┌──────────┐   ┌──────────────┐   ┌──────────────────┐
  │ Owasaka  │   │ Observability│   │ Domain Services  │
  │ SIEM (Go)│   │ TimescaleDB  │   │ (separate repos) │
  │          │   │ + Neo4j + ML │   │                  │
  │ Pipeline │   │ + Grafana    │   │ ai-agent-os      │
  │  ↓       │   │              │   │ intelagent       │
  │ BoltDB   │   └──────────────┘   │ securellm-bridge │
  │ WebSocket│                      │ cognitive-vault  │
  │ Ed25519  │                      └──────────────────┘
  │ Correl.  │
  │ ML Anom. │
  └──────────┘
```

---

## 🔗 Cross-Repository NATS Subjects

| Subject | Publisher | Subscriber | Purpose |
|---------|-----------|------------|---------|
| `neotron.compliance.sentinel.v1` | Neotron (Python) | Owasaka (Go) | Layer 1 guardrail results |
| `neotron.compliance.bastion.v1` | Neotron (Python) | Owasaka (Go) | Layer 2 kernel enforcement |
| `neotron.cortex.consensus.v1` | Neotron (Python) | Owasaka (Go) | Layer 3 swarm decisions |
| `neotron.compliance.violation.v1` | Neotron (Python) | Owasaka (Go) | Blocking violations |
| `neotron.compliance.temporal.v1` | Neotron (Python) | Owasaka (Go) | Layer 0 temporal guard |
| `neotron.compliance.siem.v1` | Neotron (Python) | Owasaka (Go) | SIEM export bridge |
| `llm.request.v1` | securellm-bridge | Spectre | LLM gateway events |
| `inference.request.v1` | ml-offload-api | Spectre | ML inference events |
| `task.assigned.v1` | IntelAgent | Spectre | Agent task dispatch |
| `quality.report.v1` | IntelAgent | Spectre | Quality gate results |

---

## 📊 Status Matrix

| Repository | Language | Build | Tests | NATS | Docs | Prod Ready |
|-----------|----------|-------|-------|------|------|------------|
| **neotron** | Python | ✅ | ✅ | ✅ (optional) | ✅ | ⬜ (Phase 3) |
| **spectre** | Rust | ✅ | ✅ | ✅ | ✅ | ✅ (Phase 4) |
| **owasaka** | Go | ✅ | ✅ | ✅ | ✅ | ✅ |
| **IP-Guard** | Rust | ⚠️ (skeleton) | ❌ | ❌ | ✅ | ❌ |
| **IntelAgent** | Rust | ✅ | ✅ | ❌ | ✅ | ⬜ |

---

## 🛠️ Cross-Repo Development Commands

```bash
# ── NATS Infrastructure ──────────────────────────────
nats-server -js                          # Start NATS with JetStream
nats pub neotron.compliance.test.v1 '{"test":true}'  # Test publish
nats sub "neotron.compliance.>"         # Watch all compliance events

# ── Spectre Proxy ───────────────────────────────────
cd /home/kernelcore/master/spectre
nix develop --command cargo run -p spectre-proxy     # Start proxy :3000
curl http://localhost:3000/health                    # Health check

# ── Neotron → Spectre ──────────────────────────────
export SPECTRE_PROXY_URL="http://localhost:3000"
export SPECTRE_JWT_SECRET="neotron-secret"
cd /home/kernelcore/master/neotron
python -m neutron.cli.main siem test --target file    # Test SIEM export

# ── Owasaka SIEM ───────────────────────────────────
cd /home/kernelcore/master/owasaka
make run                                              # Start SIEM

# ── Full Pipeline Test ─────────────────────────────
# Terminal 1: nats-server -js
# Terminal 2: cd spectre && cargo run -p spectre-proxy
# Terminal 3: cd owasaka && make run
# Terminal 4: cd neotron && python -m neutron.cli.main siem test
```

---

## 📐 Architecture Decisions

| ADR | Repository | Title | Status |
|-----|-----------|-------|--------|
| ADR-0001 | neotron | Landlock LSM replaces seccomp-only BASTION | ✅ Accepted |
| ADR-0002 | neotron | NATS as cross-codebase event bus | ⬜ Proposed |
| ADR-0003 | neotron | ZK circuit framework (Circom vs Noir) | ⬜ Proposed |
| ADR-0062 | owasaka | Ed25519 event signing | ✅ Accepted |
| ADR-0063 | owasaka | Merkle transparency log | ✅ Accepted |
| ADR-0001–0011 | spectre | Various (NATS, RBAC, Helm, SBOM, etc.) | ✅ 11 accepted |

---

## 🚨 Known Gaps

| Gap | Impact | Fix |
|-----|--------|-----|
| Spectre Proxy TLS not implemented | No encryption in transit | Implement axum-server with tls-rustls |
| NATS auth not enforced | Any local process can publish | Enable NKey auth on NATS server |
| Neotron → Spectre JWT shared secret | Static secret in env var | Integrate spectre-secrets key rotation |
| IP Guard all `todo!()` | No license verification | Phase 1 Rust implementation |
| No end-to-end integration test | Cross-repo failures undetected | Create umbrella test suite |

---

## 📈 Roadmap (Cross-Repo)

See `ROADMAP.md` for the full 5-phase plan. This document is the **architecture reference** that the roadmap executes against.

---

> **Next**: Create MCP tools for cross-repo operations (build, test, status, grep)
