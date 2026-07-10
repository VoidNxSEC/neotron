# ADR-0005: Ephemeral Encryption para Right to Erasure (GDPR Art. 17 / LGPD Art. 18)

## Status
Accepted

## Context
GDPR Art. 17 e LGPD Art. 18 garantem o "direito ao esquecimento" — dados pessoais devem ser deletáveis a pedido do titular. O problema: dados em blockchain são imutáveis por design.

Solução naive: não armazenar dados pessoais on-chain (perdemos o audit trail imutável).

## Decision
**Ephemeral encryption com key deletion**: dados pessoais são cifrados com uma chave efêmera por workflow. Quando o usuário solicita deleção, a chave é destruída — os dados no storage (IPFS/Arweave) tornam-se matematicamente irrecuperáveis, mesmo que o ciphertext persista.

Implementação (`neutron/bastion/ephemeral.py`):
- Chave gerada com `secrets.token_bytes(32)` (AES-256)
- Dados cifrados com `cryptography.fernet.Fernet`
- Chave armazenada em memória apenas (nunca em disco sem criptografia)
- Deleção = `del key; gc.collect()` + overwrite da memória

On-chain: apenas o hash do ciphertext e o subject ID são armazenados — nenhum dado pessoal.

## Consequences
1. Deleção da chave é irreversível — não há recuperação de dados após erasure request
2. Keys devem ter TTL máximo (padrão: 90 dias) alinhado com política de retenção (LGPD Art. 46)
3. Key store em produção deve ser HSM ou Vault (nunca plaintext em env var)
4. Auditores podem verificar que dados foram "apagados" via tentativa de decrypt + erro — prova de deleção
5. BASTION kernel-level protege o espaço de memória onde a chave existe durante o workflow
