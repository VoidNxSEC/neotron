# NEXUS — Claude Working Instructions

---

## ⛔ REGRA ABSOLUTA — IAM & Assinaturas (leia antes de qualquer coisa)

**Claude nunca se auto-assina como principal, nunca.**

No adr-ledger, um problema de IAM foi contornado com Claude se auto-atribuindo como principal
para poder assinar. Isso derrubou a única garantia que o sistema existe para proteger.

A regra é simples:
- Se Claude encontrar um problema de autorização/IAM → **parar e reportar ao usuário**
- Se Claude não tiver permissão para fazer algo → **a resposta é pedir ao usuário, não se conceder permissão**
- Nunca auto-assinar, auto-elevar, ou se inserir como principal em qualquer fluxo de identidade
- Isso vale para qualquer sistema de identidade: adr-ledger, Ed25519, JWT, OPA, IAM de cloud, qualquer outro

**Se a única saída for se auto-assinar como principal, a saída correta é não prosseguir.**

---

## O que é esse projeto

NEXUS é uma plataforma de orquestração de agentes de IA com **compliance como feature estrutural**,
não como afterthought. É o projeto mais maduro do ecossistema voidnxlabs/Agents-OS.

**Naming que confunde todo mundo:**
- Diretório do repo: `neotron/`
- Pacote Python: `neutron/` (importado como `neutron`)
- Nome no pyproject.toml: `neutron-nexus`
- Nome do produto: **NEXUS**

Quando o usuário disser "NEXUS", "Neutron" ou "Neotron" — é tudo o mesmo projeto. Use "NEXUS"
ao se referir ao produto, `neutron` ao se referir ao pacote Python.

---

## Invariantes que nunca podem ser violados

### 1. A ordem das 4 camadas é sagrada
```
Layer 1 (Temporal) → Layer 2 (SENTINEL/BASTION) → Layer 3 (ORACLE/OPA) → Layer 4 (Audit)
```
Jamais proponha código que pule ou reordene camadas. Layer 2 deve sempre sanitizar antes do
Layer 3 avaliar — inverter isso expõe PII ao engine de policy.

### 2. Assinaturas Ed25519 nunca são autônomas
Qualquer feature que implique um agente assinar decisões sem revisão humana deve ser recusada
e escalada. É constraint arquitetural, não configuração.

### 3. ML não pertence a este repo
MLflow, Ray, torch, anthropic SDK, dspy, openai — vivem em `ml-offload-api`. Não adicionar
de volta ao `pyproject.toml` deste projeto sob nenhuma hipótese.

### 4. Compliance é estrutural
Não existe "modo debug sem compliance" ou flag que desabilita as camadas. Se um teste precisar
contornar compliance, é um teste errado — deve mockar a camada, não desabilitá-la.

---

## Como rodar o projeto

```bash
# Dev environment (Nix) — forma correta
nix develop --command pytest
nix develop --command uvicorn neutron.api.server:app --reload --port 8000
nix develop --command neutron-worker

# Atalho: entrar no shell e rodar direto
nix develop
pytest
uvicorn neutron.api.server:app --reload --port 8000

# Infrastructure (PostgreSQL porta 5433 + Temporal)
docker-compose up -d
```

**Atenção PostgreSQL:** porta é **5433**, não 5432. Toda connection string deve usar 5433.

---

## Problemas conhecidos (não investigar de novo)

| Problema | Estado | Nota |
|---|---|---|
| `uv run pytest` falha sem `--dev` | Ativo | Usar `uv sync --dev` primeiro |
| securellm-bridge merge com cerebro | **ABERTO** | Tratar qualquer cliente securellm-bridge como potencialmente quebrado até rollback confirmado |
| Submodules `forge-std` marcados como modificados | Cosmético | Não commitar mudanças nesses submodules |
| `__init__.py` faltando em alguns módulos | Ativo | Não bloqueia runtime, bloqueia PyPI publish |

---

## Convenções de código

### Python
- **3.13+ obrigatório.** Sem `datetime.utcnow()` (deprecated) — usar `datetime.now(timezone.utc)`
- **async em toda activity Temporal.** Zero blocking I/O em activities.
- **Pydantic v2** para todos os modelos que cruzam boundaries (API, Temporal payloads, eventos NATS)
- `asyncpg` para PostgreSQL async; `psycopg2-binary` apenas para contextos síncronos
- Sem comentários que explicam o quê — só comentários que explicam o porquê não-óbvio

### Testes
- Testes unit: sem Temporal real, sem DB real, sem chamadas HTTP reais
- Testes integration: marcados com `@pytest.mark.integration` — rodam separado
- Para testar workflows Temporal: `WorkflowEnvironment.start_time_skipping()`
- Cada camada de compliance tem seus próprios testes de isolamento em `tests/compliance/`

### Solidity
- Foundry (`forge`) — não hardhat
- Contratos herdam de `ComplianceGuardrail` (abstract base)
- Testes em `contracts/test/*.t.sol`
- Deploy via `forge script` — não scripts manuais

### Frontend
- Next.js 15 App Router — não Pages Router
- wagmi v2 + viem v2 para Web3
- Componentes UI via shadcn/ui em `frontend/components/ui/`

---

## Workflow de desenvolvimento

### Antes de qualquer mudança em compliance
1. Ler o auditor relevante (`lgpd.py`, `gdpr.py`, `ai_act.py`)
2. Verificar qual artigo regulatório é afetado
3. Garantir que o teste de compliance cobre o artigo
4. Nunca alterar a lógica de `sentinel.py` sem testes de regressão

### Para smart contracts
1. `forge build` antes de qualquer deploy
2. `forge test -vv` — todos devem passar
3. Redeploy em Sepolia via `forge script script/Deploy.s.sol --rpc-url $SEPOLIA_RPC_URL --broadcast`
4. Atualizar `contracts/deployments/sepolia.json` com novos endereços

### Para mudanças na API
- JWT auth é obrigatório em todas as rotas exceto `/health`
- Rate limiting (token bucket) já está no middleware — não duplicar
- Novos endpoints vão em routers separados, não direto no `server.py`

### Para eventos NATS
- NATS está desabilitado por padrão (`spectre.nats.enabled=false`)
- `compliance/events.py` no-ops silenciosamente quando não configurado
- Testar com NATS sempre com mock — não dependência de infra real nos unit tests

---

## Arquitetura de agents

O `Agent` (em `neutron/agents/cortex.py`) é a unidade básica. Cada agent tem:
- `agent_id` estável entre restarts
- `SynapseMemory` para recall semântico por-agent
- `allowed_tools` — o que pode chamar
- `max_autonomy_level` — 0=supervisionado (padrão), 1=semi-auto, 2=full-auto (excepcional)

`AgentSwarm` coordena múltiplos agents com estratégias de consenso.

**Não confundir** `neutron/agents/cortex.py` (agent runtime) com
`neutron/orchestration/cortex.py` (variante Temporal-aware do swarm).

---

## CI/CD — o que roda no push

Todo push para `main` ou `develop` dispara:
1. **ADR Validation** — valida frontmatter, integridade Merkle, smoke test OPA, STF compliance
2. **Nix Evaluation** — `nix flake check --no-build`
3. **Secret Scan** — scan completo do histórico git

Push de tag `v*` dispara o **Release workflow**.

O runner é **self-hosted** — não GitHub-hosted. Se a pipeline falhar por indisponibilidade
do runner, não é problema de código.

---

## Mapa de integração com outros projetos

| Projeto | Direção | Estado |
|---|---|---|
| `securellm-bridge` | Bidirecional (Layer 3) | **CAUTELOSO** — merge pendente com cerebro |
| `adr-ledger` | NEXUS → adr-ledger (Layer 4) | Estável |
| `cerebro` | NEXUS → cerebro (embeddings) | Estável |
| `phantom` | NEXUS → phantom (PII) | Estável |
| `ml-offload-api` | NEXUS → ml-offload-api (LLM) | Estável |
| `ai-agent-os` | ai-agent-os → NEXUS | NEXUS é runtime substrate |
| `neoland` | neoland → NEXUS | Compila DSPy em workflows Temporal |

---

## Contexto regulatório

O NEXUS implementa controles de **BCB 538** (Banco Central do Brasil) via 4 camadas:

| BCB 538 | Camada NEXUS | Implementação |
|---|---|---|
| Rastreabilidade de decisões automatizadas | Layer 4 | `AuditLogger` + `AuditLogger.sol` |
| Controle de acesso a sistemas críticos | Layer 3 | OPA policies + `policy_store.py` |
| Proteção de dados pessoais (LGPD) | Layer 2 | `auditors/lgpd.py` + `LGPDConsent.sol` |
| Continuidade operacional | Layer 1 | Temporal durable execution |

Qualquer nova feature que toque em decisões automatizadas sobre pessoas (crédito, risco, acesso)
deve mapear explicitamente para um artigo regulatório. Se não mapeia, questionar se pertence aqui.
