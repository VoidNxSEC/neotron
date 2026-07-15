---
name: nexus
description: >
  Deep technical reference for NEXUS — enterprise AI agent orchestration platform with
  compliance-as-code. Use when working on agent orchestration, the 4-layer compliance engine
  (SENTINEL/BASTION/ORACLE/Temporal), smart contracts (Solidity/Foundry), the Next.js frontend,
  FastAPI backend, PostgreSQL memory, NATS events, Nix flake, CI/CD pipelines, or any
  development, debugging, or architectural work in this codebase.
---

# NEXUS — Enterprise AI Agent Orchestration

**Product name:** NEXUS  
**Repo directory:** `neotron/`  
**Python package:** `neutron` (pyproject name: `neutron-nexus`)  
**License:** Apache-2.0 (VoidNXLabs)  
**Python:** 3.13+ mandatory  
**LOC:** ~12,277 Python + Solidity + TypeScript  
**Status:** Beta / delivered — most architecturally mature component in the Agents-OS layer  

NEXUS is the compliance-first AI agent orchestration runtime. Every agent action passes through
four enforcement layers before producing externally visible effects. Compliance is structural —
not configurable.

---

## Monorepo Layout

```
neotron/
├── neutron/                    # Python package (core runtime)
│   ├── agents/                 # CORTEX agent engine + SYNAPSE memory
│   ├── api/                    # FastAPI server + route modules
│   ├── compliance/             # SENTINEL guardrails + BASTION kernel + auditors
│   ├── core/                   # Config, models, SOPS secrets
│   ├── memory/                 # PostgreSQL episodic + working memory
│   ├── orchestration/          # Temporal workflows + worker bootstrap
│   ├── reasoning/              # ORACLE explainability engine
│   ├── storage/                # Decentralized storage (IPFS/Arweave)
│   ├── cli/                    # `neutron` CLI entry point
│   ├── plugins/
│   └── ml-lab/                 # cerebro_optimizer.py
├── contracts/                  # Solidity smart contracts (Foundry)
│   ├── src/                    # 6 contracts (see below)
│   ├── test/                   # Forge tests
│   ├── script/Deploy.s.sol
│   └── deployments/sepolia.json
├── frontend/                   # Next.js 15 + React 19 + wagmi/viem
│   ├── app/                    # Pages
│   ├── components/             # UI components
│   └── lib/                    # Hooks, contract bindings, wagmi config
├── tests/                      # pytest suite (unit + integration + compliance)
├── scripts/                    # Demo scripts (4layer, bastion, cortex, nexus, sentinel…)
├── demos/                      # eu_ai_act_demo.py, test_4layer_flow.py
├── docs/                       # Architecture, planning, reports, security
├── config/integrations.yaml    # cerebro / phantom / spectre / NATS config
├── docker-compose.yml          # PostgreSQL 15 + Temporal 1.22.4
├── flake.nix                   # Nix flake (Python 3.13, eBPF deps)
├── pyproject.toml              # hatchling build; uv lock
├── foundry.toml
├── justfile / Makefile
└── .github/workflows/          # 4 CI workflows (see CI/CD section)
```

---

## Architecture: The 4-Layer Compliance Model

Every agent action flows bottom-to-top through four enforcement planes. **No layer can be skipped.**

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 4 — Audit & Provenance                                │
│  AuditLogger (PostgreSQL) + DecentralizedStorage (IPFS/Arweave)│
│  On-chain: AuditLogger.sol + ComplianceGuardrail.sol        │
├──────────────────────────────────────────────────────────────┤
│  Layer 3 — Policy Enforcement (ORACLE + OPA)                 │
│  ORACLE explainability engine, oracle_endpoints.py           │
│  policy_store.py + policy_endpoints.py                       │
├──────────────────────────────────────────────────────────────┤
│  Layer 2 — Data Sanitization + Guardrails (SENTINEL/BASTION) │
│  ComplianceGuardrail, LGPD/GDPR/AI-Act auditors             │
│  BASTION: BPF kernel-level enforcement (bastion.py)          │
│  On-chain: LGPDConsent.sol                                   │
├──────────────────────────────────────────────────────────────┤
│  Layer 1 — Workflow Orchestration (Temporal)                 │
│  Durable execution, saga patterns, retry/timeout logic       │
│  orchestration/workflows.py + orchestration/worker.py        │
└──────────────────────────────────────────────────────────────┘
         ↑ All agent actions flow bottom-to-top ↑
```

**Critical invariant:** Layer ordering is always 1→2→3→4. Skipping Layer 2 before Layer 3 means
OPA/ORACLE may receive raw PII — an irrecoverable compliance breach.

---

## Python Package: `neutron/`

### `neutron/agents/`

| File | Key classes | Purpose |
|---|---|---|
| `cortex.py` | `Agent`, `ConsensusEngine`, `AgentSwarm`, `AgentResponse`, `ConsensusStrategy` | Primary agent runtime; swarm coordination and consensus |
| `synapse.py` | `SynapseMemory`, `MemoryItem` | Per-agent semantic recall (cosine similarity, in-process vector store) |
| `document_agent.py` | `DocumentIngestionAgent` | Specialized agent for document ingestion flows |
| `_llm_http_client.py` | `LLMHTTPClient`, `_LLMResponse` | HTTP client for LLM calls (routes via ml-offload-api) |
| `specialized/base_agent.py` | `BaseAgent` protocol | Base class all specialized agents implement |
| `specialized/compliance_analyst.py` | `ComplianceAnalystAgent` | Compliance-focused agent |
| `specialized/decision_maker.py` | `DecisionMakerAgent` | Decision-making agent |
| `specialized/risk_assessor.py` | `RiskAssessorAgent` | Risk assessment agent |

### `neutron/compliance/`

| File | Key classes / functions | Purpose |
|---|---|---|
| `sentinel.py` | `ComplianceGuardrail`, `ValidationResult`, `AgentOutput`, `EnforcedOutput`, `ComplianceViolation`, `create_guardrail()` | Core SENTINEL guardrail engine — validates every agent output |
| `bastion.py` | `BPFInstruction`, `BPFProgram`, `KernelPolicy`, `LayeredPolicy`, `ComplianceCapability`, `grant_capability()`, `revoke_capability()`, `has_capability()` | BASTION kernel-level BPF enforcement |
| `nexus_flow.py` | `NEXUSComplianceFlow`, `ComplianceRequest`, `ComplianceResponse`, `LayerResult`, `ComplianceDecision` | Orchestrates the full 4-layer compliance pipeline |
| `audit_logger.py` | `AuditLogger` | Writes structured compliance events to PostgreSQL |
| `events.py` | `publish()` (async), `publish_sync()` | NATS event bus publish (optional; `spectre.nats.enabled=false` by default) |
| `auditors/lgpd.py` | `check_lgpd_article_18_explanation()`, `check_lgpd_article_20_portability()`, `get_lgpd_guardrails()`, `validate_with_lgpd()` | LGPD Art. 18 + 20 auditors |
| `auditors/lgpd_kernel.py` | `grant_lgpd_consent()`, `revoke_lgpd_consent()`, `check_lgpd_consent()`, `get_lgpd_kernel_policies()` | Kernel-level LGPD consent lifecycle |
| `auditors/gdpr.py` | `check_gdpr_article_22_human_oversight()`, `check_gdpr_article_15_data_access()`, `check_gdpr_article_17_erasure_support()`, `GDPRErasureHandler`, `get_gdpr_guardrails()` | GDPR Art. 15, 17, 22 auditors |
| `auditors/ai_act.py` | `AISystemRiskLevel`, `classify_ai_system_risk()`, `check_ai_act_article_13_transparency()`, `check_ai_act_article_14_human_oversight()`, `check_ai_act_prohibited_practices()`, `validate_ai_act_compliance()` | EU AI Act Art. 5, 13, 14 auditors |

### `neutron/api/`

FastAPI application with JWT auth, rate limiting (token bucket), and the following routers:

| Router | Prefix | Purpose |
|---|---|---|
| `auth_endpoints.py` | (inline) | Login, token issue |
| `policy_endpoints.py` | — | OPA policy CRUD |
| `audit_endpoints.py` | — | Audit log retrieval |
| `consent_endpoints.py` | — | LGPD consent management |
| `compliance.py` | — | Compliance check endpoints |
| `oracle_endpoints.py` | `/v1/oracle` | `POST /v1/oracle/explain` — ORACLE explainability |

**Direct routes on `app` (server.py):**
```
GET  /health
POST /api/v1/tasks
GET  /api/v1/tasks/{task_id}
GET  /api/v1/agents
POST /api/v1/agents/execute
POST /api/v1/swarm/execute
GET  /api/v1/compliance/status
GET  /v1/metrics
POST /v1/test/cortex
```

### `neutron/orchestration/`

| File | Key classes | Purpose |
|---|---|---|
| `workflows.py` | `validate_agent_output_activity()`, `batch_validate_outputs_activity()` | Temporal activities wrapping SENTINEL validation |
| `cortex.py` | `AgentSwarm`, `ConsensusEngine`, `Task`, `AgentResult`, `SwarmResult` | Temporal-aware swarm orchestration |
| `worker.py` | `main()` | Temporal worker bootstrap (entry: `neutron-worker`) |

### `neutron/memory/`

| File | Key classes | Purpose |
|---|---|---|
| `memory_store.py` | `MemoryStore`, `Memory`, `MemorySearchResult`, `create_memory_store()` | PostgreSQL-backed agent memory with vector search |
| `episodic.py` | `EpisodicMemory`, `MemoryModel` (SQLAlchemy ORM) | Long-term episodic memory |
| `working.py` | — | Short-term working memory |

### `neutron/reasoning/`

**ORACLE** — Explainability engine with 5 strategies:

| Class | `ExplanationType` | Strategy |
|---|---|---|
| `FeatureImportanceExplainer` | `FEATURE_IMPORTANCE` | Ranks input features by contribution |
| `CounterfactualExplainer` | `COUNTERFACTUAL` | "What would change the decision?" |
| `ExampleBasedExplainer` | `EXAMPLE_BASED` | Similar historical cases |
| `ChainOfThoughtExplainer` | `CHAIN_OF_THOUGHT` | Step-by-step reasoning trace |
| `RuleBasedExplainer` | `RULE_BASED` | Explicit rule firing |

Factory: `create_explainer(explanation_type)`, `explain_agent_decision()`

### `neutron/storage/`

`DecentralizedStorage` — hybrid on-chain/off-chain audit storage:
- **IPFS** (`StorageType.IPFS`): mutable, cheaper, requires pinning
- **Arweave** (`StorageType.ARWEAVE`): permanent (~200 years), one-time cost
- `StorageReceipt`, `ComplianceLog` models

### `neutron/core/`

| File | Key classes | Purpose |
|---|---|---|
| `config.py` | `NEXUSConfig`, `LLMConfig`, `ProviderConfig`, `ProviderType`, `get_config()`, `reload_config()` | Singleton config (env + SOPS) |
| `models.py` | `HyperparameterSpace`, `PipelineConfig`, `TrainingConfig`, `OptimizationState`, `SearchStrategy` | Core data models |
| `sops.py` | — | SOPS secrets connector |

---

## Smart Contracts (`contracts/src/`)

**Framework:** Foundry (`forge`). **Network:** Sepolia testnet.

| Contract | Deployed address | Purpose |
|---|---|---|
| `LendingProtocol.sol` | `0x35fF603BD286E287f932356316271D59a4ADa779` | DeFi lending — collateral 150%, interest 500bps, liquidation threshold 120% |
| `LGPDConsent.sol` | (inherits ComplianceGuardrail) | On-chain LGPD consent lifecycle (Art. 7, 16, 46) |
| `AuditLogger.sol` | — | Compliance events on-chain with IPFS/Arweave off-chain refs |
| `ComplianceGuardrail.sol` | abstract | Base with compliance modifiers + errors for all contracts |
| `EmergencyStop.sol` | — | Circuit breaker for emergency halts |
| `PriceOracle.sol` | — | Price feed for LendingProtocol |

**Deployer:** `0x017d2F22c2Ac860b775Ad6e9c1E3C1945ac69BE7`  
**Chain ID:** 11155111 (Sepolia)

**LGPD on-chain semantic — critical:** `revokeConsent` uses `address(this)` as processor, not `msg.sender`. This was a bug fixed in commit `9bde70a`. Always verify processor address semantics in new consent code.

---

## Frontend (`frontend/`)

**Stack:** Next.js 15.1, React 19, wagmi 2.14, viem 2.21, Tailwind CSS, shadcn/ui

**Pages (`frontend/app/`):**

| Page | Route | Purpose |
|---|---|---|
| `page.tsx` | `/` | Dashboard |
| `assistant/page.tsx` | `/assistant` | AI agent assistant with approval dialog |
| `borrow/page.tsx` | `/borrow` | Borrow flow |
| `lend/page.tsx` | `/lend` | Deposit/lend flow |
| `loans/page.tsx` | `/loans` | Loan management |
| `liquidate/page.tsx` | `/liquidate` | Liquidation interface |
| `compliance/page.tsx` | `/compliance` | Compliance status + audit trail |

**Key components:**
- `compliance/ComplianceLayers.tsx` — visual 4-layer status
- `compliance/AuditTrail.tsx` — audit log display
- `compliance/LGPDConsentModal.tsx` — LGPD consent UX
- `assistant/ApprovalDialog.tsx` — human approval gate for supervised agent actions
- `web3/WalletRequired.tsx`, `web3/NetworkGuard.tsx` — Web3 guards

**Wagmi hooks (`frontend/lib/hooks/`):** `useBorrow`, `useDeposit`, `useLiquidate`, `useLoanHealth`, `usePoolStatus`, `useRepay`, `useUserLoans`, `useWithdraw`

---

## Infrastructure & Config

### Docker Compose

```yaml
services:
  postgres:    # PostgreSQL 15-alpine — port 5433, db=neutron, user=neutron
  temporal:    # temporalio/auto-setup:1.22.4 — gRPC 7233, UI 8088
               # backed by postgres; dynamic config in temporal-config/
```

ML services (MLflow, Ray) **moved to `ml-offload-api`** — not in this compose file.

### `config/integrations.yaml`

```yaml
cerebro.optimizer:
  model: "claude-3-5-sonnet-20241022"   # LLM for hyperparameter suggestions
  enabled: true
phantom.cortex:
  enabled: false                         # Multi-agent consensus — OFF by default
spectre.nats:
  enabled: false                         # NATS event bus — OFF by default
  url: "nats://localhost:4222"
```

### Nix Flake (`flake.nix`)

- Systems: `x86_64-linux`, `aarch64-linux`
- Python 3.13 via nixpkgs
- eBPF deps: `linuxPackages.bcc`, `bpftools`, `libbpf` (requires kernel BTF: `CONFIG_DEBUG_INFO_BTF=y`)
- `hardeningDisable = ["stackprotector"]` for BPF maps
- Scripts: `nix/scripts/` (flake-scaffold, nix-build-debug, system-analyzer)

---

## CI/CD Pipelines (`.github/workflows/`)

### 1. ADR Validation & Enforcement
Triggers: push/PR to `main`, `develop`. Runner: self-hosted.

Jobs:
- **validate-adrs** — frontmatter check (`id`, `title`, `status`), status/directory alignment, ID conflict detection, no placeholder content in accepted ADRs
- **chain-integrity** — Merkle chain verification (`python .chain/chain_manager.py verify`), SHA-256 tamper detection on signed ADRs
- **enforcement-smoke** — OPA authz smoke test (`tests/smoke_enforcement.sh`)
- **detect-features** — commit feature detection (`.hooks/feature_detector.py`), integration check (`.hooks/integration_checker.py`)
- **stf-compliance-check** — STF protocol schema validation (`.stf/neutron.stf`, `.schema/stf.schema.json`); min 4 directives + 4 constraints
- **code-quality** — TODO/FIXME scan, executable permissions on critical scripts
- **sync-knowledge-base** — on push to `main`: regenerates `knowledge/*.json` from ADRs via `.parsers/adr_parser.py`
- **summary** — final pass/fail aggregation

### 2. Nix Evaluation
Triggers: push/PR to `main`, `develop`.
- `nix flake check --no-build` on self-hosted runner

### 3. Publish GitHub Release
Triggers: push of `v*` tags.
- Creates GitHub Release; uses `RELEASE-{tag}.md` if present, auto-generates otherwise

### 4. Secret Scan
Triggers: push to `main`, `og`; PRs to `main`; manual.
- `bash scripts/phantom-scan-check.sh .` — full git history scan for secrets

---

## Test Suite (`tests/`)

```
tests/
├── agents/         test_cortex.py, test_specialized.py
├── api/            test_audit.py, test_auth.py, test_consent.py, test_policies.py
├── compliance/
│   ├── auditors/   test_ai_act.py, test_gdpr.py, test_lgpd.py, test_lgpd_kernel.py
│   ├── test_bastion.py, test_sentinel.py, test_workflow_integration.py
├── integration/    test_4layer_integration.py, test_full_workflow.py
├── memory/         test_memory_store.py, test_working.py
├── orchestration/  test_cortex.py
├── reasoning/      test_oracle.py
├── storage/        test_decentralized.py
├── test_trainers.py, test_workflows.py
└── conftest.py
```

**pytest config:** `addopts = "-v --tb=short -m 'not integration'"` — integration tests skipped by default.
**Temporal testing:** Use `WorkflowEnvironment.start_time_skipping()` for unit-style workflow tests.

---

## Entry Points (`pyproject.toml [project.scripts]`)

```
neutron          → neutron.cli.main:main
neutron-worker   → neutron.orchestration.worker:main
neutron-gui      → neutron.gui.app:main
neutron-dag      → neutron.integration.dag_bridge:main
```

---

## Key Dependencies

```toml
temporalio    >=1.6.0    # Durable workflow engine
pydantic      >=2.6.0    # All data models crossing boundaries
pydantic-settings >=2.2.0
fastapi       >=0.110.0
uvicorn[standard] >=0.27.0
psycopg2-binary >=2.9.9  # PostgreSQL sync (use asyncpg for async contexts)
sqlalchemy    >=2.0.0
python-dotenv >=1.0.0
PyYAML        >=6.0.3
click         >=8.1.0
```

**ML deps removed from this package** — moved to `ml-offload-api/python/pyproject.toml`.

---

## Regulatory Compliance Mapping

| Regulation | Articles Implemented | Layer | Implementation |
|---|---|---|---|
| LGPD | Art. 7 (consent), 18 (explanation), 20 (portability), 46 (retention) | 2 + on-chain | `auditors/lgpd.py`, `LGPDConsent.sol` |
| GDPR | Art. 15 (access), 17 (erasure), 22 (human oversight) | 2 | `auditors/gdpr.py` |
| EU AI Act | Art. 5 (prohibited), 13 (transparency), 14 (oversight) | 2 | `auditors/ai_act.py` |
| BCB 538 | Rastreabilidade, controle de acesso, LGPD, continuidade | 1+2+3+4 | Full 4-layer stack |

---

## Critical Known Issues & Constraints

1. **securellm-bridge merge (OPEN):** An erroneous merge with cerebro occurred. All `securellm-bridge` client code in this repo should be treated as potentially broken until surgical rollback is confirmed. Validate interface contracts before any calls.

2. **LendingProtocol deployed on Sepolia only** — not mainnet. Frontend `.env.local` must point to Sepolia RPC.

3. **NATS disabled by default** — `spectre.nats.enabled=false`. `compliance/events.py` no-ops silently when NATS is not configured.

4. **eBPF in Nix sandbox** — BPF syscalls are blocked by `nix build`. eBPF code must be excluded from `nix build` checks and tested outside the sandbox.

5. **Temporal activity timeouts** — always set explicit `start_to_close_timeout`. Default is unlimited; agent LLM calls can hang indefinitely.

6. **ML layer removed** — MLflow, Ray, torch, anthropic SDK, dspy are not in this package. They live in `ml-offload-api`. Do not add them back here.

7. **PostgreSQL port** — exposed on **5433** (not 5432). Connection strings must use port 5433.

---

## Debugging Quick Reference

```bash
# Temporal
temporal workflow list --namespace default
temporal workflow show --workflow-id <id>
temporal workflow terminate --workflow-id <id> --reason "debug"

# PostgreSQL
psql -h localhost -p 5433 -U neutron -d neutron

# OPA policy test
opa eval -i input.json -d policy.rego "data.nexus.authz.allow"

# Nix flake check
nix flake check --no-build

# Run tests (unit only)
uv run pytest
# Run with integration
uv run pytest -m integration

# Start API server
uv run uvicorn neutron.api.server:app --reload --port 8000

# Start Temporal worker
uv run neutron-worker

# Foundry
cd contracts && forge build
forge test -vv
forge script script/Deploy.s.sol --rpc-url $SEPOLIA_RPC_URL --broadcast
```

---

## Glossary

| Term | Meaning |
|---|---|
| NEXUS | Product name (formerly Neotron/Neutron); internal platform codename |
| SENTINEL | Application-layer compliance guardrail engine (`compliance/sentinel.py`) |
| BASTION | Kernel-level BPF enforcement (`compliance/bastion.py`) + on-chain (`ComplianceGuardrail.sol`) |
| ORACLE | Explainability engine (`reasoning/oracle.py`) — 5 explanation strategies |
| CORTEX | Agent swarm engine (`agents/cortex.py`) |
| SYNAPSE | Per-agent semantic memory (`agents/synapse.py`) |
| ComplianceGuardrail | Python: runtime validator; Solidity: abstract base contract with modifiers |
| Activity | Temporal unit of work — single agent action with retry/timeout |
| Workflow | Temporal durable process — coordinates activities across an agent task |
| Saga | Compensating transaction pattern — rollback chain for failed multi-step workflows |
| ml-offload-api | Separate repo/service — all ML inference (LLM calls, embeddings, Ray, MLflow) |
