# ADR-0003: ZK Circuit Framework — Circom como Primary, Noir como Fallback

## Status
Accepted

## Context
O IP Guard precisa gerar e verificar zero-knowledge proofs de compliance de licença sem revelar:
- A identidade do detentor da licença
- O ID específico do NFT de licença

Candidatos avaliados:
| Framework | Linguagem | Prova | Gas Verif. | Maturidade | Tooling Nix |
|-----------|-----------|-------|------------|------------|-------------|
| **Circom** | DSL | Groth16 | ~200k gas | Alta (Hermez, Zcash) | Parcial |
| **Noir** | Rust-like | PLONK | ~300k gas | Média (Aztec) | Boa |
| **Halo2** | Rust | PLONK | ~250k gas | Alta | Boa |
| **RISC Zero** | Rust | STARK | ~500k gas | Nova | Boa |

## Decision
**Circom 2.1.6 + Groth16 + snarkjs** como implementação primária.
**Noir** mantido como `compliance.nr` para comparação e fallback.

Justificativa:
1. Groth16 tem o menor gas cost de verificação on-chain (~200k vs ~300k Plonk)
2. `circomlib` tem Poseidon hash nativo (necessário para o commitment scheme)
3. snarkjs gera `Verifier.sol` automaticamente — integra com Foundry sem adaptadores
4. Menor curva de aprendizado (muita documentação, Tornado Cash como referência)

## Consequences
1. Trusted setup ceremony necessária (Powers of Tau Phase 1 pré-computada, Phase 2 por circuito)
2. Prover roda em Node.js/WASM — pode ser lento em hardware fraco
3. `zk-commons` crate abstrai o prover em Rust via process::Command para snarkjs
4. Noir mantido em `circuits/compliance.nr` para migração futura se gas costs mudarem
5. Qualquer novo circuito deve ter equivalente `.nr` documentado como ADR de migração
