# ADR-0002: NATS como Event Bus Cross-Codebase

## Status
Accepted

## Context
O ecossistema NEXUS é composto por 5 repositórios em linguagens distintas (Python, Rust, Go, TypeScript). Precisamos de um mecanismo de comunicação assíncrona que:
- Suporte múltiplos publishers e subscribers simultâneos
- Seja agnóstico de linguagem
- Tenha baixa latência (< 500ms)
- Permita fanout (um evento → múltiplos consumidores)
- Funcione tanto em dev local quanto em produção

Alternativas consideradas: gRPC (acoplamento forte), Kafka (overhead operacional alto), Redis Pub/Sub (sem persistência), NATS (leve, multi-linguagem, JetStream para persistência).

## Decision
Usar **NATS** como event bus central para toda comunicação cross-repo no NEXUS umbrella.

- **Subjects padronizados**: `neotron.compliance.*.v1`, `spectre.events.*`, `ipguard.*`
- **JetStream** para eventos que precisam de persistência/replay (audit trail)
- **Queue groups** para load balancing entre múltiplas instâncias do mesmo serviço
- **NKey auth** para autenticação zero-trust (ADR-0002-ext: G5)

## Consequences
1. Todos os repos devem ter um client NATS nativo (nats-py, async-nats, nats.go)
2. Subjects seguem o padrão `<repo>.<domain>.<type>.v<N>` — versionado por design
3. Consumers devem ser idempotentes (mensagens podem ser re-entregues via JetStream)
4. Serviço NATS deve estar UP antes de qualquer integração — `just infra-up` inclui isso
5. Auth via NKey garante que processos locais não-autorizados não publicam em produção
