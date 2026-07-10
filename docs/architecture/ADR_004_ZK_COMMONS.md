# ADR-0004: zk-commons — Crate Compartilhada de Infraestrutura ZK

## Status
Accepted

## Context
Tanto IP Guard quanto IntelAgent precisam de ZK proofs:
- IP Guard: prova de posse de licença sem revelar identidade
- IntelAgent: prova de qualidade de output (`quality_proof`) e compliance (`compliance_proof`)

Sem extração, cada repo duplicaria: circuit compilation, trusted setup management, witness generation, proof serialization.

## Decision
Extrair `zk-commons` como crate Rust compartilhada em `IP-Guard/crates/zk-commons/`.

Interface pública:
```rust
pub trait CircuitBuilder { fn build(&self) -> Circuit; }
pub trait Prover { fn prove(&self, circuit: &Circuit, witness: &Witness) -> Proof; }
pub trait Verifier { fn verify(&self, proof: &Proof, public_inputs: &[Field]) -> bool; }
pub struct ComplianceCircuit { ... }  // compliance.circom wrapper
pub struct QualityCircuit { ... }     // quality_proof circuit (IntelAgent)
```

Estratégia de prover: `snarkjs` via `std::process::Command` (Node.js WASM) — evita compilar bellman/arkworks em Nix (complexo).

## Consequences
1. Tanto IP Guard CLI quanto IntelAgent importam `zk-commons` como Cargo dependency
2. Mudanças no trusted setup ceremony afetam ambos — deve ser versionado junto com o circuito
3. `zk-commons` não publica prova para NATS diretamente — provas são retornadas como bytes e o caller decide o transporte
4. Circuit files (`.r1cs`, `.zkey`, `verification_key.json`) são assets — versionados em `circuits/` de cada repo
5. Publish no crates.io fora do escopo por ora — dependência via path/git
