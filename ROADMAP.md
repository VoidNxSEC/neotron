# NEXUS Platform — Roadmap Consolidado

> **Last updated**: 2026-05-21  
> **Scope**: Neotron (Python) + IP Guard (Rust) + IntelAgent (Rust) + SPECTRE (Rust)  
> **Principle**: One roadmap. Four projects. Zero drift.

---

## 🗺️ Ecosystem Map

```
/home/kernelcore/
├── master/neotron/                    ← THIS REPO
│   ├── neutron/                         Neotron CLI + API + Agents + BASTION + SENTINEL
│   │   ├── cli/                           ✅ 50+ comandos, 16 grupos
│   │   ├── bastion/                       ✅ Landlock LSM (landlock.py)
│   │   ├── security/                      ✅ git_scanner + nix_checker
│   │   ├── compliance/                    ✅ SENTINEL (LGPD guardrails)
│   │   ├── orchestration/                 ✅ CORTEX (Temporal workflows)
│   │   ├── events/                        ⚠️ NATS Bridge (parcial — SPECTRE proxy integration) 
│   │   ├── siem/                            ✅ CEF/JSON/Syslog export 
│   │   └── spectre/                         ✅ SPECTRE Proxy HTTP client
│   ├── IP-Guard/                        ⭐ Nix + Blockchain + ZK → agora unificado
│   │   ├── crates/ip-guard-core/          ⚠️  Skeleton (lib.rs), todo!() nos submodulos
│   │   ├── contracts/IPGuard.sol          ❌ [DEPRECATED — substituído por LicenseRegistry]
│   │   └── contracts/ZKVerifier.sol       ❌ [DEPRECATED]
│   └── contracts/src/supplychain/         ✅ SBOM + Build + License + Guardian (4 contratos)
│   └── flake.nix                        Nix dev shell
│
└── arch/phantom-nx/libs/              ← O ARSENAL (repo separado) [DEPRECATED — use /master/spectre]
    ├── phantom-soc-kernel/              IntelAgent — Core + ZK + DAO
    │   ├── core/                          ✅ Agent, Task, QualityGate, Context, Proof
    │   ├── quality/                       ✅ Quality Gates, Peer Review
    │   ├── security/                      ✅ Audit, Privacy
    │   ├── governance/dao/                ⬜ Algorand PyTeal contracts
    │   ├── governance/rewards/            ⬜ Reward distribution
    │   └── mcp/                           ⬜ MCP server implementations
│
├── master/owasaka/                  ← OWASAKA SIEM (Go)
│   ├── internal/events/neotron.go      ✅ Severity-aware subscriber
│   ├── internal/events/pipeline.go     ✅ EventCompliance routing
│   └── internal/events/neotron_test.go ✅ 6/6 tests
│
├── master/spectre/                  ← SPECTRE Fleet (Rust) — Phase 4
│   ├── crates/spectre-proxy/           ✅ JWT+RBAC :3000
│   └── crates/spectre-events/          ✅ 30+ event types
│
├── master/securellm-mcp/            ← MCP Server (TypeScript)
│   └── src/tools/umbrella-tools.ts     ✅ 4 cross-repo tools + sentinel
│
├── master/sentinel/                  ← Integration Test Suite (Python)
│   └── 10 scenarios                    ✅ Registered in umbrella registry
    └── spectre-rust/                    SPECTRE Fleet — Event Bus + Secrets + Proxy
        ├── spectre-core/                  ✅ Types, errors, config, logging
        ├── spectre-events/                ✅ 30+ event types, NATS client, pub/sub
        ├── spectre-secrets/               ⬜ Secret rotation (PHASE 4)
        ├── spectre-proxy/                 ⬜ Zero-Trust gateway (PHASE 4)
        └── spectre-observability/         📅 Phase 2 — TimescaleDB + Neo4j + ML
```

---

## 📊 Status Summary

| Project | Language | Fase 0 (Foundation) | Fase 1 (Security/ZK) | Fase 2+ (Integration) |
|---------|----------|---------------------|----------------------|-----------------------|
| **Neotron** | Python | ✅ CLI + BASTION + SENTINEL + CORTEX + SIEM | ⚠️ NATS Bridge (via SPECTRE Proxy) + ⬜ Ephemeral + Namespaces | ⬜ |
| **Owasaka** | Go | ✅ SIEM + Pipeline + Subscriber | ✅ EventCompliance + Neotron integration | ✅ |
| **IP Guard** | Rust → Solidity | ⚠️ Rust skeleton | ✅ Contracts compilados (SupplyChain) | ⬜ |
| **IntelAgent** | Rust | ✅ Core + Quality + Security | ⬜ ZK Circuits + DAO + MCP | ⬜ |
| **SPECTRE** | Rust | ✅ Core + Events + Proxy (Phase 4) | ⬜ Secrets | ⬜ Observability |

---

## 🧭 PHASE 1 — Foundation Unificada (Days 1-10)

> **Goal**: Eliminar todos os `todo!()` do IP Guard, criar NATS Bridge, shared infrastructure.

### Track A: NATS Bridge (Neotron Python)

| ID | Task | Days | Depends On | Blocker For |
|----|------|------|------------|-------------|
| A1 | Criar `neutron/events/__init__.py` — NATS client wrapper com `nats-py` | 0.5 | — | A2, A3 |
| A2 | Criar `neutron/events/bridge.py` — Python ↔ Rust type mapping (event schemas) | 0.5 | A1 | A3 |
| A3 | Criar `neutron/events/cli_commands.py` — `neotron event {emit,subscribe,list}` | 0.5 | A2 | B1 |
| A4 | Integration test: emit from Neotron CLI → received by SPECTRE listener | 0.5 | A3 | — |

- [x] A1 — `neutron/events/__init__.py`
- [x] A2 — `neutron/events/bridge.py`
- [x] A3 — `neotron event` CLI commands
- [x] A4 — Integration test NATS bridge

### ✅ Track A Complete (4/4 tasks)

### Track B: IP Guard Core (Rust)

| ID | Task | Days | Depends On | Blocker For |
|----|------|------|------------|-------------|
| B1 | Implementar `nix.rs` — parser de derivation Nix real (hash, meta.license, SPDX) | 2 | — | B3 |
| B2 | Implementar `blockchain.rs` — RPC client Ethereum/Polygon com ethers-rs | 1.5 | — | B3 |
| B3 | Implementar `lib.rs` — `verify_license_compliance()` funcional (sem ZK ainda) | 1 | B1, B2 | B4 |
| B4 | Implementar `cli/main.rs` — `ip-guard verify <flake.nix>` funcional | 0.5 | B3 | B5 |
| B5 | Teste end-to-end: Anvil local + deploy IPGuard.sol + verify derivation real | 1 | B4 | — |

- [x] B1 — `nix.rs` derivation parser
- [x] B2 — `blockchain.rs` RPC client
- [x] B3 — `lib.rs` core logic
- [x] B4 — CLI `verify` command
- [ ] B5 — E2E test (Anvil + contract + derivation)

### ✅ Track B Complete (4/5 tasks — B5 needs running Anvil)

---

## 🔐 PHASE 2 — ZK Pipeline Compartilhada (Days 11-20)

> **Goal**: Circuit Circom real + trusted setup + on-chain verification. Extrair `zk-commons` shared crate.

| ID | Task | Days | Depends On | Blocker For |
|----|------|------|------------|-------------|
| C1 | Redesenhar `compliance.circom` — prova: "hash X tem licença Y válida sem revelar identidade" | 3 | — | C2, C3 |
| C2 | Noir alternative `compliance.nr` (comparar Circom vs Noir) | 1 | C1 | — |
| C3 | Trusted setup ceremony (Powers of Tau) + witness generation | 1.5 | C1 | C4 |
| C4 | Implementar `zk.rs` — integração Circom → Rust (wasm ou RPC para prover) | 2 | C3 | C5 |
| C5 | Substituir `ZKVerifier.sol` dummy por verificação Groth16 real | 1.5 | C3 | C6 |
| C6 | E2E test: `ip-guard verify --zk` → proof → submit → on-chain verification | 1 | C4, C5 | — |
| C7 | Extrair `zk-commons` crate (CircuitBuilder, Prover trait, Verifier trait) | 1.5 | C6 | IntelAgent ZK |
| C8 | Documentar ZK pipeline (architecture decision + trusted setup guide) | 0.5 | C6 | — |

- [x] C1 — `compliance.circom` real
- [x] C2 — Noir alternative
- [x] C3 — Trusted setup + witness
- [x] C4 — `zk.rs` Circom integration
- [x] C5 — `ZKVerifier.sol` Groth16 real
- [ ] C6 — E2E ZK test
- [x] C7 — `zk-commons` shared crate
- [x] C8 — ZK pipeline docs

### ✅ Phase 2 Complete (7/8 tasks — C6 needs Anvil + trusted setup)

---

## 🔗 PHASE 3 — Integração & Compliance (Days 21-28)

> **Goal**: Neotron CLI chama IP Guard via NATS. Fechar paradoxos do Red Team.

| ID | Task | Days | Depends On | Blocker For |
|----|------|------|------------|-------------|
| D1 | `neotron license verify <path>` — CLI command via NATS → IP Guard | 1 | A3, B4 | D5 |
| D2 | `neotron license status` — consulta licenças verificadas (cache local + on-chain) | 0.5 | D1 | — |
| D3 | Ephemeral encryption — `neutron/bastion/ephemeral.py` (Right to Erasure GDPR/LGPD) | 3 | — | — |
| D4 | Namespace isolation — Landlock profiles per workflow (`neutron/bastion/namespaces.py`) | 2 | — | — |
| D5 | IntelAgent ZK circuits — reusa `zk-commons` para `quality_proof`, `compliance_proof` | 4 | C7 | IntelAgent Fase 2 |
| D6 | Regression tests: BASTION blocks unauthorized access + SENTINEL blocks PII | 1 | D3, D4 | — |

- [x] D1 — `neotron license verify`
- [x] D2 — `neotron license status`
- [x] D3 — Ephemeral encryption (Right to Erasure)
- [x] D4 — Namespace isolation (Landlock per workflow)
- [x] D5 — IntelAgent ZK circuits (quality_proof)
- [x] D6 — Regression tests (BASTION + SENTINEL)

### ✅ Phase 3 Complete (6/6 tasks)

---

## 🛡️ PHASE 4 — SPECTRE Arsenal (Days 29-36)

> **Goal**: Secrets rotation + Zero-Trust proxy. SPECTRE production-ready.

| ID | Task | Days | Depends On | Blocker For |
|----|------|------|------------|-------------|
| E1 | `spectre-secrets` — extrair crypto do cognitive-vault, secret rotation automática | 4 | A3 (NATS) | E2 |
| E2 | `spectre-proxy` — Zero-Trust gateway (TLS mutual + auth + rate limiting) | 4 | E1 | — |
| E3 | Integrate `spectre-secrets` with IP Guard key management | 1 | E1, C4 | — |
| E4 | Integrate `spectre-proxy` with Neotron API gateway | 1 | E2 | — |

- [x] E1 — `spectre-secrets` crate
- [x] E2 — `spectre-proxy` crate
- [x] E3 — IP Guard key management via spectre-secrets
- [x] E4 — Neotron API via spectre-proxy

### ✅ Phase 4 Complete (4/4 tasks)

---

## 🚀 PHASE 5 — Production Hardening (Days 37-50)

> **Goal**: Deploy, monitor, scale. NixOS modules, multi-chain, dashboards.

| ID | Task | Days | Depends On | Blocker For |
|----|------|------|------------|-------------|
| F1 | IP Guard NixOS module — deploy declarativo (`nix/modules/ip-guard.nix`) | 2 | B5, C6 | — |
| F2 | Multi-chain deployment — Polygon + Arbitrum (IPGuard.sol + ZKVerifier.sol) | 2 | C5 | — |
| F3 | IntelAgent DAO — Algorand PyTeal smart contracts | 5 | D5 | — |
| F4 | SPECTRE observability — TimescaleDB + Neo4j + ML anomaly detection | 5 | E2 | — |
| F5 | Dashboard — Grafana compliance metrics + license status | 3 | F1, F4 | — |
| F6 | CI/CD pipeline — GitHub Actions para IP Guard + Neotron | 2 | B4, D1 | — |

- [x] F1 — IP Guard NixOS module
- [ ] F2 — Multi-chain (Polygon, Arbitrum)
- [ ] F3 — IntelAgent DAO (Algorand PyTeal)
- [ ] F4 — SPECTRE observability
- [ ] F5 — Grafana dashboard
- [ ] F6 — CI/CD pipeline

### 🟡 Phase 5 Started (1/6 tasks)

---

## 🎯 Success Criteria

### Phase 1 (Foundation)
- [ ] `neotron event emit audit.decision` → received by SPECTRE listener in < 500ms
- [ ] `ip-guard verify <flake.nix>` → returns license NFT ID + compliance status
- [ ] All `todo!()` in IP Guard crates resolved

### Phase 2 (ZK Pipeline)
- [ ] `ip-guard verify --zk` → generates Groth16 proof → verifies on-chain in < 3s
- [ ] ZK proof size < 1KB
- [ ] Gas cost per verification < $0.01 (L2)
- [ ] `zk-commons` crate published and reusable by IntelAgent

### Phase 3 (Integration)
- [ ] `neotron license verify` works end-to-end (CLI → NATS → IP Guard → Blockchain)
- [ ] Ephemeral key deletion makes on-chain data irrecoverable (GDPR Art. 17 compliant)
- [ ] Namespace isolation prevents workflow A from reading workflow B files

### Phase 4 (SPECTRE)
- [ ] Secret rotation completes without downtime
- [ ] Zero-Trust proxy blocks unauthenticated requests

### Phase 5 (Production)
- [ ] NixOS module deploys IP Guard in < 2 min
- [ ] Dashboard shows real-time compliance status
- [ ] CI/CD all green on main

---

## 📋 Dependency Graph

```
A1 ──→ A2 ──→ A3 ──→ A4 ────────────────┐
                                          ├──→ D1 ──→ D2
B1 ──→ B3 ──→ B4 ──→ B5                  │
B2 ──┘                         │         │
                               ↓         │
C1 ──→ C3 ──→ C4 ──→ C6 ──→ C7 ─────────┘
        │      │                   ↓
        ↓      ↓              D5 (IntelAgent ZK)
       C2     C5 ──→ C6       │
                              ↓
D3 ──→ D6                    F3 (IntelAgent DAO)
D4 ──┘

A3 ──→ E1 ──→ E2 ──→ E4 ──→ F4 ──→ F5
        │      │
        ↓      ↓
       E3     F4
```

---

## ⚠️ Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Circom toolchain breaks on NixOS | Medium | High | Maintain Noir alternative (C2) |
| ethers-rs API churn (v2 → v3) | Medium | Medium | Pin version in Cargo.toml |
| NATS bridge latency > 500ms | Low | Medium | Use queue groups + connection pooling |
| ZK trusted setup takes too long | Medium | Medium | Pre-compute Phase 1 during dev |
| Algorand PyTeal learning curve | High | Medium | Start with Solidity prototype first |
| Cross-repo coordination overhead | High | Low | This roadmap is the single source of truth |

---

## 📐 Architecture Decisions (ADRs Needed)

- [ ] **ADR-0002**: NATS as cross-codebase event bus (Neotron ↔ SPECTRE ↔ IP Guard)
- [ ] **ADR-0003**: ZK circuit framework selection (Circom vs Noir)
- [ ] **ADR-0004**: Shared ZK infrastructure (`zk-commons` crate)
- [ ] **ADR-0005**: Ephemeral encryption for Right to Erasure compliance
- [ ] **ADR-0006**: Landlock namespace isolation per workflow
- [ ] **ADR-0007**: IP Guard placement in ecosystem (standalone product vs shared infra)

---

## 📈 Progress Tracker

| Phase | Status | Start | Target | Progress |
|-------|--------|-------|--------|----------|
| Phase 1: Foundation | 🟡 In Progress | — | Day 10 | 8/9 tasks |
| Phase 2: ZK Pipeline | 🟢 Completed | Day 11 | Day 20 | 7/8 tasks |
| Phase 3: Integration | 🟢 Completed | Day 21 | Day 28 | 6/6 tasks |
| Phase 4: SPECTRE | 🟢 Completed | Day 29 | Day 36 | 4/4 tasks |
| Phase 5: Production | 🟡 In Progress | Day 37 | Day 50 | 1/6 tasks |

**Total**: 33 tasks across 5 phases, est. 50 days

### ✅ Completed (Session 2026-05-21)

| ID | Task | Status |
|----|------|--------|
| **SIEM Export** | | |
| S1 | neutron/siem/ module (CEF/LEEF/JSON/Syslog + File/Syslog/NATS) | ✅ |
| S2 | neotron siem CLI group (status, export, tail, test) | ✅ |
| **Owasaka SIEM** | | |
| S3 | EventCompliance type + neotron.go severity subscriber | ✅ |
| S4 | pipeline.go compliance routing + transparency log | ✅ |
| S5 | neotron_test.go (6 tests passing) | ✅ |
| **SPECTRE Proxy Client** | | |
| S6 | neutron/spectre/client.py (JWT + circuit breaker + retry) | ✅ |
| S7 | neutron/compliance/events.py SPECTRE_PROXY_URL routing | ✅ |
| **Supply Chain Contracts** | | |
| S8 | SBOMRegistry.sol (CycloneDX/SPDX on-chain) | ✅ Compiled |
| S9 | BuildAttestation.sol (SLSA Level 0-3) | ✅ Compiled |
| S10 | LicenseRegistry.sol (ERC-721 + SPDX + ZK — IP Guard 2.0) | ✅ Compiled |
| S11 | SupplyChainGuardian.sol (orchestrator — une todos) | ✅ Compiled |
| **MCP Umbrella Tools** | | |
| S12 | umbrella-tools.ts — project_context_switcher | ✅ Build + testado |
| S13 | umbrella-tools.ts — cross_project_search | ✅ Build + testado |
| S14 | umbrella-tools.ts — dependency_graph_analyzer | ✅ Build + testado |
| S15 | umbrella-tools.ts — context_window_optimizer | ✅ Build + testado |
| S16 | sentinel project added to umbrella registry | ✅ |
| **Documentation** | | |
| S17 | ECOSYSTEM.md (222 linhas, 12 repos) | ✅ |
| S18 | ROADMAP.md updated | ✅ |
| S19 | plans/langmath-owasaka-integration.md updated | ✅ |

---

> **ROADMAP 1 encerrado em 2026-05-31. Ver ROADMAP 2 abaixo.**

---

---

# NEXUS Platform — Roadmap 2

> **Started**: 2026-05-31  
> **Scope**: Neotron + SPECTRE + IP Guard + IntelAgent + Supply Chain  
> **Principle**: Fechar dívidas técnicas → observabilidade → segurança → enterprise.

## 📊 Status ROADMAP 1 (herança)

| Item | Status |
|------|--------|
| Fase 5 F2: Multi-chain (Polygon + Arbitrum) | ❌ pendente → G4 |
| Fase 5 F3: IntelAgent DAO | ❌ pendente → Fase 4 |
| Fase 5 F4: SPECTRE observability | ❌ pendente → H1 |
| Fase 5 F5: Grafana dashboard | ❌ pendente → H2 |
| Fase 5 F6: CI/CD GitHub Actions | ❌ pendente → G1 |
| C6: E2E ZK test (Anvil + Groth16) | ❌ pendente → G3 |
| B5: E2E IP Guard test | ❌ pendente → G3 |
| Supply Chain contracts E2E | ❌ compilados sem deploy/test → H4 |
| LangMath BERT embeddings | ❌ apenas features sintáticas → Fase 3 |
| NATS NKey auth | ❌ gap de segurança → G5 |
| SPECTRE Proxy TLS | ❌ gap de segurança → G6 |
| JWT shared secret → rotação | ❌ gap de segurança → H5 |

---

## 🔧 FASE 1 — Fechar Pendências Críticas (Days 1–14)

> **Goal**: quitar dívidas técnicas que bloqueiam todo o resto.

| ID | Task | Dias | Depende De |
|----|------|------|------------|
| G1 | CI/CD GitHub Actions — pipeline completo (test, lint, forge test, nix check, release) | 3 | — |
| G2 | ADRs 0002–0007 — aceitar formalmente | 1 | — |
| G3 | B5 + C6 — E2E ZK test com Anvil local (script `just e2e-zk`) | 3 | G1 |
| G4 | Multi-chain: deploy `LicenseRegistry.sol` + `ZKVerifier.sol` em Polygon Mumbai + Arbitrum Sepolia | 3 | G3 |
| G5 | NATS NKey auth — habilitar autenticação + atualizar `neutron/events/bridge.py` | 2 | — |
| G6 | SPECTRE Proxy TLS — `axum-server` com `tls-rustls` | 2 | — |

- [x] G1 — CI/CD pipeline
- [x] G2 — ADRs formalizados (0002–0007, todos Accepted)
- [ ] G3 — E2E ZK test
- [ ] G4 — Multi-chain deploy
- [x] G5 — NATS NKey auth (credentials file > nkey seed > token)
- [x] G6 — SPECTRE TLS (tokio-rustls + hyper-util, TLS_ENABLED=true)

---

## 📡 FASE 2 — Observabilidade & Supply Chain CLI (Days 15–28)

| ID | Task | Dias | Depende De |
|----|------|------|------------|
| H1 | SPECTRE observability — TimescaleDB + Neo4j + ML anomaly detection | 5 | G6 |
| H2 | Grafana dashboard — compliance metrics + license status + ZK proofs | 3 | H1 |
| H3 | Supply Chain CLI — `neotron sbom generate`, `neotron attest build`, `neotron supply-chain verify` | 3 | — |
| H4 | Supply Chain E2E test — Anvil + pipeline Nix → SBOMRegistry → BuildAttestation | 2 | H3, G3 |
| H5 | JWT rotation — integrar `spectre-secrets` (substituir static secret) | 2 | G6 |

- [ ] H1 — SPECTRE observability
- [ ] H2 — Grafana dashboard
- [ ] H3 — Supply Chain CLI
- [ ] H4 — Supply Chain E2E
- [ ] H5 — JWT rotation

---

## 🧮 FASE 3 — LangMath Production (Days 29–40)

| ID | Task | Dias | Depende De |
|----|------|------|------------|
| I1 | BERT embeddings reais — `sentence-transformers` / `fastembed` | 3 | — |
| I2 | CORTEX integration — `LinguisticAlgebra` como analyzer plugin | 2 | I1 |
| I3 | API endpoint — `POST /api/v1/langmath/analyze` | 1 | I2 |
| I4 | CLI — `neotron langmath analyze <text>` | 1 | I3 |
| I5 | Testes LangMath — 30+ casos | 2 | I4 |

- [ ] I1 — BERT embeddings
- [ ] I2 — CORTEX plugin
- [ ] I3 — API endpoint
- [ ] I4 — CLI command
- [ ] I5 — 30+ testes

---

## 🏛️ FASE 4 — IntelAgent DAO (Days 41–56)

> **Decisão**: Arbitrum Sepolia (Solidity) ao invés de Algorand PyTeal — elimina nova toolchain, reusa ZK existente.

| ID | Task | Dias | Depende De |
|----|------|------|------------|
| J1 | ADR formal: Algorand vs Arbitrum Solidity | 1 | G2 |
| J2 | DAO contract — proposta, votação, quórum, execução | 5 | J1 |
| J3 | Reward distribution — token ERC-20 para agentes que passam QualityGate | 3 | J2 |
| J4 | IntelAgent MCP server — `task.assign`, `quality.report`, `dao.vote` via NATS | 3 | J3 |
| J5 | Integration test — CORTEX → IntelAgent → DAO → reward E2E | 2 | J4 |

- [ ] J1 — ADR DAO framework
- [ ] J2 — DAO contract
- [ ] J3 — Reward token
- [ ] J4 — MCP server
- [ ] J5 — E2E integration

---

## 🔒 FASE 5 — Security Audit & Hardening (Days 57–70)

| ID | Task | Dias | Depende De |
|----|------|------|------------|
| K1 | Slither/Echidna — audit estático + fuzzing em todos os contracts | 2 | G4 |
| K2 | CodeQL + Semgrep — scan Python + Rust | 2 | G1 |
| K3 | Threat model — STRIDE para os 4 layers (`docs/security/THREAT_MODEL.md`) | 2 | — |
| K4 | Penetration test checklist — `neutron/tests/pentest/` | 2 | K3 |
| K5 | Dependency audit — `pip-audit` + `cargo audit` + `npm audit` no CI | 1 | G1 |
| K6 | Secrets scan — `gitleaks` pre-commit hook em `flake.nix` | 1 | — |

- [ ] K1 — Slither/Echidna
- [ ] K2 — CodeQL/Semgrep
- [ ] K3 — Threat model
- [ ] K4 — Pentest checklist
- [ ] K5 — Dependency audit
- [ ] K6 — Gitleaks hook

---

## ☸️ FASE 6 — Enterprise & Kubernetes (Days 71–84)

| ID | Task | Dias | Depende De |
|----|------|------|------------|
| L1 | Helm chart — API + worker + temporal (baseado em `spectre/charts/`) | 4 | H1 |
| L2 | NixOS module — `nix/modules/neotron.nix` | 2 | — |
| L3 | Operational runbooks — `docs/ops/` (deploy, rollback, incident, scaling) | 2 | L1 |
| L4 | Performance benchmarks — CORTEX <500ms, SENTINEL >1000 req/s, ZK <$0.01 gas | 2 | H2 |
| L5 | Compliance certification artifacts — SOC2 + ISO 27001 via CI | 3 | K2, L4 |

- [ ] L1 — Helm chart
- [ ] L2 — NixOS module
- [ ] L3 — Runbooks
- [ ] L4 — Benchmarks
- [ ] L5 — Certification artifacts

---

## 🎯 Métricas de Sucesso (ROADMAP 2)

| Métrica | Target |
|---------|--------|
| CI/CD tempo total | < 15 min |
| ZK proof E2E | < 3s, < 1KB, < $0.01 gas |
| CORTEX consensus latência | < 500ms |
| SENTINEL throughput | > 1000 req/s |
| Test coverage | ≥ 90% mantido |
| Security findings críticos | 0 |
| Grafana dashboards | ≥ 3 (compliance + license + ZK) |

## 📈 Progress Tracker (ROADMAP 2)

| Fase | Status | Dias | Progress |
|------|--------|------|----------|
| Fase 1: Pendências Críticas | 🟡 In Progress | 1–14 | 4/6 |
| Fase 2: Observabilidade | ⬜ Planned | 15–28 | 0/5 |
| Fase 3: LangMath | ⬜ Planned | 29–40 | 0/5 |
| Fase 4: IntelAgent DAO | ⬜ Planned | 41–56 | 0/5 |
| Fase 5: Security Audit | ⬜ Planned | 57–70 | 0/6 |
| Fase 6: Enterprise/K8s | ⬜ Planned | 71–84 | 0/5 |

**Total**: 32 tasks, 84 dias estimados
