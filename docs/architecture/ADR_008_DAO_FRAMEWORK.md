# ADR-0008: IntelAgent DAO — Arbitrum Solidity ao invés de Algorand PyTeal

## Status
Accepted

## Context
A Fase 5 do ROADMAP 1 previa "IntelAgent DAO via Algorand PyTeal". Na prática, Algorand introduziria:
- Nova toolchain (PyTeal + Algorand SDK) sem nenhum overlap com o stack atual
- Novo modelo de contas (não-EVM) — incompatível com `ethers-rs`, `cast`, `forge`
- Bridging cross-chain complexo para integrar com os contratos EVM já existentes
- Curva de aprendizado alta listada explicitamente no Risk Register do ROADMAP 1

Alternativas avaliadas:
| Framework | EVM-compatível | Reusa toolchain | Gas cost | Maturidade |
|-----------|---------------|-----------------|----------|------------|
| **Arbitrum Solidity** | ✅ | ✅ Foundry + cast | Baixo (L2) | Alta |
| Algorand PyTeal | ❌ | ❌ Nova toolchain | Baixo | Média |
| Cosmos CosmWasm | ❌ | ❌ Nova toolchain | Médio | Média |
| Solana Anchor | ❌ | ❌ Nova toolchain | Muito baixo | Alta |

## Decision
**Arbitrum Sepolia + Solidity** para o IntelAgent DAO.

Contratos:
- `contracts/src/dao/AgentRewardToken.sol` — ERC-20 soulbound (mintado pelo DAO)
- `contracts/src/dao/IntelAgentDAO.sol` — governance: registro, proposta, votação, execução

Integração com o ecossistema existente:
- Herda `ComplianceGuardrail` → AI Act Art. 13 (transparência) + Art. 14 (oversight) enforçados on-chain
- Usa `AuditLogger` → toda proposta executada gera audit log imutável
- Compatível com `ZKVerifier` → provas de qualidade verificáveis on-chain futuramente

## Consequences
1. Deploy em Arbitrum Sepolia via `forge script` — mesmo fluxo dos outros contratos
2. Gas costs < $0.001 por votação em L2 (Arbitrum)
3. Algorand descartado permanentemente — não reabre sem novo ADR
4. DAO on-chain é o único mecanismo para mint de `AgentRewardToken` — sem backdoor
5. Quórum inicial = 50% dos agentes registrados (ajustável via proposta)
6. Timelock = 1 bloco (dev) / 24h (prod) antes de execução de propostas aprovadas
