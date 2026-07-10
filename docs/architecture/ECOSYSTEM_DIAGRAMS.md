# NEXUS / Neotron — Diagramas da Arquitetura

**Status:** Living document  
**Última atualização:** 2026-04-08  
**Propósito:** Visualizar o ecossistema completo (Neotron + IntelAgent + SPECTRE)

---

## 1. Visão Macro: O Ecossistema Completo

```mermaid
graph TB
    subgraph "NEXUS Platform — /home/kernelcore/master/neotron/"
        direction TB
        CLI["🎮 neotron CLI<br/>50+ comandos<br/>Python/Click"]
        API["🌐 FastAPI Server<br/>REST + Docs<br/>Python/Uvicorn"]
        WORKER["⚙️ Temporal Worker<br/>Durable Execution<br/>Python"]
        GUI["🖥️ GUI<br/>Python"]
        
        subgraph "4-Layer Defense"
            L1["🛡️ SENTINEL<br/>App-level validation<br/>GDPR/LGPD policies"]
            L2["🛡️ BASTION<br/>Kernel seccomp-BPF<br/>Syscall filtering"]
            L3["🛡️ BASTION-SC<br/>Smart Contracts<br/>On-chain compliance"]
            L4["🛡️ AUDIT TRAIL<br/>IPFS + Arweave<br/>Immutable logs"]
        end
        
        AGENTS["🧠 Cortex Agents<br/>Swarm Consensus<br/>majority/unanimous/weighted"]
        MEMORY["💾 Episodic Memory<br/>pgvector"]
        COMPLIANCE["📋 Compliance Engine<br/>Policy validation"]
    end

    subgraph "IntelAgent — /home/kernelcore/arch/phantom-nx/libs/phantom-soc-kernel/"
        direction TB
        CORE["🔷 Core<br/>Agent • Task • QualityGate<br/>Context • Proof"]
        QUALITY["✅ Quality Gates<br/>Peer Review<br/>Brainstorm Protocol"]
        PRIVACY["🔐 Privacy<br/>Circom ZK Circuits<br/>Data Commitments"]
        GOVERNANCE["🏛️ Governance<br/>Algorand DAO<br/>Token Economics ($INTEL)"]
        MCP["📡 MCP Servers<br/>Project Memory<br/>Quality Metrics"]
        AUDIT["📜 Audit Trail<br/>Immutable Ledger<br/>Compliance Reports"]
    end

    subgraph "SPECTRE Fleet — /home/kernelcore/arch/phantom-nx/libs/spectre-rust/"
        direction TB
        EVENTS["📨 NATS Event Bus<br/>30+ event types<br/>Pub/Sub + Queue Groups"]
        PROXY["🔒 Spectre Proxy<br/>Zero-Trust Gateway<br/>TLS • Auth • Rate Limit"]
        SECRETS["🗝️ Spectre Secrets<br/>Rotation Engine<br/>AES-GCM • Argon2"]
        OBSERVABILITY["📊 Observability<br/>TimescaleDB • Neo4j<br/>ML Anomaly Detection"]
        CORE2["🔷 Spectre Core<br/>ServiceId • TraceId<br/>Config • Logging"]
    end

    CLI --> API
    CLI --> WORKER
    API --> AGENTS
    WORKER --> AGENTS
    AGENTS --> L1
    L1 --> L2
    L2 --> L3
    L3 --> L4
    AGENTS --> MEMORY
    AGENTS --> COMPLIANCE

    EVENTS <--> PROXY
    EVENTS <--> SECRETS
    EVENTS <--> OBSERVABILITY
    PROXY --> SECRETS

    AGENTS -.->|"future NATS"| EVENTS
    L4 -.->|"on-chain proofs"| GOVERNANCE
    COMPLIANCE -.->|"audit events"| AUDIT
```

---

## 2. As 4 Camadas de Defense-in-Depth

```mermaid
graph LR
    subgraph "User Space (Python)"
        AGENT["🤖 Agent Output"]
        S1["SENTINEL<br/>Policy Check"]
        AGENT --> S1
    end

    subgraph "Kernel Space (Linux)"
        S2["BASTION<br/>seccomp-BPF<br/>+ Landlock"]
        S1 -->|"syscall"| S2
    end

    subgraph "On-Chain (EVM/Algorand)"
        S3["BASTION-SC<br/>Smart Contract<br/>Consent Check"]
        S2 -->|"attestation"| S3
    end

    subgraph "Decentralized Storage"
        S4["AUDIT TRAIL<br/>IPFS + Arweave<br/>ZK Proof"]
        S3 -->|"immutable log"| S4
    end

    style S1 fill:#4B0082,stroke:#fff,color:#fff
    style S2 fill:#8B0000,stroke:#fff,color:#fff
    style S3 fill:#DAA520,stroke:#000,color:#000
    style S4 fill:#006400,stroke:#fff,color:#fff
```

---

## 3. Fluxo de Dados: Requisição → Resposta

```mermaid
sequenceDiagram
    actor User
    participant CLI as neotron CLI
    participant API as FastAPI
    participant Worker as Temporal Worker
    participant Agent as Cortex Agent
    participant Sentinel as SENTINEL
    participant Bastion as BASTION (Kernel)
    participant SC as Smart Contract
    participant NATS as NATS (SPECTRE)
    participant Audit as Arweave/IPFS

    User->>CLI: neotron run adaptive
    CLI->>API: POST /workflow
    API->>Worker: Start Workflow
    Worker->>Agent: Execute Task
    Agent->>Sentinel: Check Output
    Sentinel->>Bastion: Syscall Filter
    Bastion->>SC: On-chain Attestation
    SC->>NATS: Publish compliance.v1
    NATS->>Audit: Store Log
    Audit-->>SC: Proof Hash
    SC-->>Bastion: Attestation OK
    Bastion-->>Sentinel: Syscall Allowed
    Sentinel-->>Agent: Policy Passed
    Agent-->>Worker: TaskResult
    Worker-->>API: Workflow Complete
    API-->>CLI: Response
    CLI-->>User: ✅ Done
```

---

## 4. SPECTRE Event Bus: Todos os Event Types

```mermaid
graph LR
    subgraph "Event Producers"
        LLM["🤖 LLM Gateway<br/>securellm-bridge"]
        ML["🧠 ML Inference<br/>ml-offload-api"]
        RAG["📚 RAG<br/>ragtex"]
        SYS["💻 System<br/>ai-agent-os"]
        TASK["📋 Orchestration<br/>intelagent"]
        GOV["🏛️ Governance<br/>DAO"]
    end

    subgraph "NATS Event Bus (spectre-events)"
        NATS_BUS["nats://localhost:4222<br/>───────────────<br/>llm.request.v1<br/>llm.response.v1<br/>inference.request.v1<br/>inference.response.v1<br/>vram.status.v1<br/>rag.query.v1<br/>document.indexed.v1<br/>system.metrics.v1<br/>system.log.v1<br/>task.assigned.v1<br/>task.result.v1<br/>governance.proposal.v1<br/>governance.vote.v1<br/>quality.report.v1<br/>cost.incurred.v1"]
    end

    subgraph "Event Consumers"
        PROXY2["🔒 Spectre Proxy"]
        OBS["📊 Observability"]
        AUDIT2["📜 Audit Trail"]
    end

    LLM --> NATS_BUS
    ML --> NATS_BUS
    RAG --> NATS_BUS
    SYS --> NATS_BUS
    TASK --> NATS_BUS
    GOV --> NATS_BUS

    NATS_BUS --> PROXY2
    NATS_BUS --> OBS
    NATS_BUS --> AUDIT2
```

---

## 5. IntelAgent Core: Abstrações e Relações

```mermaid
classDiagram
    class Agent {
        +AgentId id()
        +AgentMetadata metadata()
        +Capability can_handle(task)
        +TaskResult execute(task, context)
        +Reputation reputation()
    }
    
    class Task {
        +TaskId id
        +String description
        +TaskInput input
        +Requirements requirements
        +Constraints constraints
        +Vec~ContextQuery~ context_needed
        +Vec~QualityGate~ quality_gates
        +DateTime deadline
        +with_objective(objective)
        +with_privacy(level)
        +with_quality_gate(gate)
    }
    
    class QualityGate {
        +ValidationResult validate(result)
        +Severity severity()
        +String description()
    }
    
    class Context {
        +ProjectMemory project_memory
        +Vec~MCPServer~ mcp_servers
        +DAOState dao_state
        +AuditTrail audit_trail
    }
    
    class TaskResult {
        +TaskId task_id
        +TaskOutput output
        +f64 quality_score
        +u64 execution_time_ms
        +Option~Proof~ proof
        +Vec~String~ validation_evidence
        +String summary
    }
    
    class Proof {
        +String circuit_id
        +Vec~Field~ public_inputs
        +Vec~u8~ proof_data
        +VerificationKey verification_key
    }
    
    Agent --> Task : executes
    Agent --> Context : uses
    Agent --> TaskResult : produces
    Task --> QualityGate : validates
    TaskResult --> Proof : contains
```

---

## 6. Roadmap Cross-Codebase: Fases e Dependências

```mermaid
gantt
    title NEXUS Ecosystem Roadmap
    dateFormat YYYY-MM-DD
    axisFormat %b %d

    section Neotron (Python)
    Fase 0: CLI Unificada               :done, n0, 2026-04-01, 3d
    Fase 1a: Landlock + bpf_d_path      :n1a, 2026-04-08, 5d
    Fase 1b: Esquecimento Criptográfico  :n1b, after n1a, 5d
    Fase 1c: Namespace Isolation         :n1c, after n1b, 3d
    Fase 2: Alinhamento Narrativa        :n2, after n1c, 3d
    Fase 3: Testes de Regressão          :n3, after n2, 4d

    section SPECTRE (Rust)
    Fase 0: Core + Events (30 tipos)    :done, s0, 2026-01-01, 14d
    Fase 1a: spectre-secrets            :s1a, 2026-04-08, 4d
    Fase 1b: spectre-proxy              :s1b, after s1a, 6d
    Fase 2: spectre-observability       :s2, after s1b, 10d

    section IntelAgent (Rust)
    Fase 0: Core Abstractions           :done, i0, 2025-12-15, 14d
    Fase 1: ZK Circuits (Circom)        :i1, 2026-04-15, 14d
    Fase 2: DAO Smart Contracts         :i2, after i1, 10d
    Fase 3: MCP Servers                 :i3, after i2, 7d

    section Integration
    Neotron ↔ SPECTRE (NATS bridge)     :int1, after n1a, 5d
    Neotron ↔ IntelAgent (ZK proofs)    :int2, after i1, 5d
    E2E Tests                            :int3, after int1, 3d
```

---

## 7. Detalhe: O Paradoxo Seccomp → Correção com Landlock

```mermaid
graph TB
    subgraph "PROBLEMA (Atual)"
        PY["🐍 Python Agent<br/>open('/data/cliente_A.json')"]
        SECCOMP["❌ seccomp-BPF<br/>vê: openat(AT_FDCWD, 0x7fff..., O_RDONLY)<br/>NÃO lê o path!"]
        KERNEL1["Kernel: 'Alguém quer abrir algo'<br/>Mas não sabe O QUÊ"]
        PY --> SECCOMP --> KERNEL1
    end

    subgraph "SOLUÇÃO (Fase 1)"
        PY2["🐍 Python Agent<br/>open('/data/cliente_A.json')"]
        LANDLOCK["✅ Landlock (Linux 5.13+)<br/>Opera na camada de INODE<br/>Consegue resolver paths!"]
        BPF["✅ bpf_d_path()<br/>Resolve o path no kernel<br/>BPF_PROG_TYPE_TRACING"]
        KERNEL2["Kernel: 'openat → /data/cliente_A.json'<br/>Bloco ou permito com precisão"]
        PY2 --> LANDLOCK --> KERNEL2
        PY2 --> BPF --> KERNEL2
    end

    style SECCOMP fill:#8B0000,stroke:#fff,color:#fff
    style KERNEL1 fill:#8B0000,stroke:#fff,color:#fff
    style LANDLOCK fill:#006400,stroke:#fff,color:#fff
    style BPF fill:#006400,stroke:#fff,color:#fff
    style KERNEL2 fill:#006400,stroke:#fff,color:#fff
```

---

## 8. Detalhe: O Paradoxo Esquecimento → Correção com Chave Efêmera

```mermaid
sequenceDiagram
    participant Agent as 🤖 Agent
    participant Sentinel as 🛡️ SENTINEL
    participant DB as 💾 PostgreSQL<br/>(off-chain)
    participant ZK as 🔐 ZK Circuit
    participant Chain as ⛓️ Arweave/IPFS<br/>(on-chain)

    Note over Agent,Chain: FASE NORMAL — Log cego

    Agent->>Sentinel: AgentOutput (pode conter PII)
    Sentinel->>Sentinel: 1. Stripe PII → commitment = blake3(dado)
    Sentinel->>DB: 2. Store encrypted(dado, key_efemera)
    Sentinel->>ZK: 3. Generate ZK proof: "dado válido sem revelar"
    Sentinel->>Chain: 4. Store commitment + ZK proof (SEM PII)

    Note over Agent,Chain: DIREITO AO ESQUECIMENTO (GDPR Art.17)

    actor Titular
    Titular->>Sentinel: "Exerço meu direito ao esquecimento"
    Sentinel->>DB: 5. DELETE key_efemera
    Sentinel->>Chain: 6. Publish: "key destroyed at height N"
    Note over Chain: Dado on-chain agora é IRRECUPERÁVEL<br/>Imutabilidade técnica mantida<br/>Esquecimento prático garantido
```

---

## 9. Stack Tecnológica por Camada

```mermaid
graph TB
    subgraph "Layer 7: CLI & DX"
        NEOTRON_CLI["neotron CLI<br/>Python/Click"]
        JUSTFILE["justfile"]
        MAKEFILE["Makefile"]
    end

    subgraph "Layer 6: API & Orchestration"
        FASTAPI["FastAPI<br/>Python"]
        TEMPORAL["Temporal.io<br/>Workflow Engine"]
        GUI["Python GUI"]
    end

    subgraph "Layer 5: Agents & Intelligence"
        CORTEX["Cortex Agents<br/>Python"]
        INTELAGENT["IntelAgent Core<br/>Rust"]
        LLM["LLM Providers<br/>Anthropic/DeepSeek/OpenAI"]
    end

    subgraph "Layer 4: Compliance"
        SENTINEL2["SENTINEL Policies<br/>Python/YAML"]
        QUALITY_GATES["Quality Gates<br/>Rust"]
        ZK_PROOFS["ZK Circuits<br/>Circom/Rust"]
    end

    subgraph "Layer 3: Security"
        BASTION2["BASTION<br/>seccomp-BPF + Landlock"]
        SPECTRE_PROXY["Spectre Proxy<br/>Rust/Axum"]
        SPECTRE_SECRETS["Spectre Secrets<br/>Rust/AES-GCM"]
    end

    subgraph "Layer 2: Event Bus"
        NATS["NATS<br/>30+ event types"]
        SPECTRE_EVENTS["Spectre Events<br/>Rust"]
    end

    subgraph "Layer 1: Storage & Audit"
        POSTGRES["PostgreSQL<br/>pgvector"]
        TIMESCALE["TimescaleDB"]
        NEO4J["Neo4j"]
        ARWEAVE["Arweave/IPFS"]
        ALGORAND["Algorand DAO"]
    end

    subgraph "Layer 0: Infrastructure"
        NIX["Nix Flakes<br/>Reproducible Builds"]
        DOCKER["Docker Compose<br/>Dev Environment"]
        NIXOS["NixOS Module<br/>Production"]
    end

    NEOTRON_CLI --> FASTAPI
    FASTAPI --> TEMPORAL
    TEMPORAL --> CORTEX
    CORTEX --> SENTINEL2
    SENTINEL2 --> BASTION2
    CORTEX --> INTELAGENT
    INTELAGENT --> QUALITY_GATES
    INTELAGENT --> ZK_PROOFS
    BASTION2 --> NATS
    SPECTRE_PROXY --> NATS
    NATS --> POSTGRES
    NATS --> TIMESCALE
    NATS --> ARWEAVE
    INTELAGENT --> ALGORAND
```

---

## 10. Mapa de Decisão: O Que Fazer Primeiro

```mermaid
graph TD
    START["🎯 O que atacar na Fase 1?"]
    
    START --> A["1. Neotron: Landlock"]
    START --> B["2. SPECTRE: Secrets + Proxy"]
    START --> C["3. IntelAgent: ZK Circuits"]
    START --> D["4. Integration: NATS Bridge"]

    A --> A1["Fecha o gap Seccomp↔Python"]
    A --> A2["Pré-requisito para BASTION real"]
    A --> A3["Impacto: Segurança do Kernel"]

    B --> B1["Secrets é pré-req do Proxy"]
    B --> B2["Proxy é pré-req do Zero-Trust"]
    B --> B3["Impacto: Infraestrutura"]

    C --> C1["ZK proofs para compliance"]
    C --> C2["Depende de Circom toolchain"]
    C --> C3["Impacto: Privacidade"]

    D --> D1["Conecta Neotron ↔ SPECTRE"]
    D --> D2["Eventos do Python → NATS → Rust"]
    D --> D3["Impacto: Integração"]

    A1 --> REC["✅ RECOMENDAÇÃO:<br/>1. Neotron Landlock (5d)<br/>2. SPECTRE Secrets (4d)<br/>3. NATS Bridge (5d)<br/>4. ZK Circuits (14d)"]

    style REC fill:#006400,stroke:#fff,color:#fff
    style START fill:#4B0082,stroke:#fff,color:#fff
```

---

## Notas

- **Mermaid.js**: Esses diagramas são renderizados nativamente no GitHub, GitLab, e qualquer Markdown viewer compatível com Mermaid.
- **Atualização**: Este documento deve ser atualizado sempre que uma fase for concluída ou um diagrama ficar desatualizado.
- **ADR**: Decisões arquiteturais derivadas destes diagramas devem ser registradas como ADRs no diretório `docs/architecture/`.
