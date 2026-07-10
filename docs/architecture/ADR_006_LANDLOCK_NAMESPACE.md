# ADR-0006: Landlock LSM para Namespace Isolation por Workflow

## Status
Accepted

## Context
BASTION (Layer 2) precisa garantir que um workflow não acesse arquivos de outro workflow — isolamento de filesystem por processo. Opções:

| Mecanismo | Kernel | User-space | Granularidade | Overhead |
|-----------|--------|------------|---------------|---------|
| **Landlock LSM** | ✅ (5.13+) | ✅ (sem root) | Por path/dir | Mínimo |
| seccomp-BPF | ✅ | ✅ | Por syscall | Mínimo |
| Namespaces Linux | ✅ | ❌ (root) | Por processo | Médio |
| AppArmor/SELinux | ✅ | ❌ (root) | Por processo | Médio |
| Docker | ✅ | Parcial | Por container | Alto |

## Decision
**Landlock LSM** como mecanismo de isolamento por workflow, complementar ao seccomp-BPF já existente.

- Cada workflow Temporal recebe um perfil Landlock que define exatamente quais paths pode ler/escrever
- Três perfis padrão: `LGPD_ART7` (consent data), `LGPD_ART16` (access logs), `LGPD_ART46` (security policy)
- Implementação em `neutron/bastion/namespaces.py` via `prctl(PR_SET_SECCOMP)` + Landlock ruleset
- Vantagem crítica: **sem root required** — workflows rodam como user não-privilegiado

## Consequences
1. Kernel ≥ 5.13 requerido em produção (NixOS unstable satisfaz)
2. Violações de Landlock geram `EACCES` que o BASTION captura e publica como evento NATS
3. Não é possível retroativamente expandir o perfil sem restart do processo — design intencional
4. Performance: overhead < 2% mensurado em benchmarks de I/O (ver `docs/ops/benchmarks.md`)
5. Compatível com Temporal workers: cada activity function pode ter seu próprio ruleset
