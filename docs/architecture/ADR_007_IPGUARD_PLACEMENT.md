# ADR-0007: IP Guard — Produto Standalone com Integração via NATS

## Status
Accepted

## Context
IP Guard (Nix + Blockchain + ZK license compliance) pode ser posicionado de duas formas:

**Opção A: Infraestrutura compartilhada** — IP Guard é uma biblioteca interna, cada repo chama diretamente.
- Pro: sem latência de rede
- Con: cada repo carrega toda a toolchain Rust + Blockchain; mudanças quebrando todos

**Opção B: Produto standalone** — IP Guard roda como serviço independente, outros repos interagem via NATS.
- Pro: isolamento total, deployável separadamente, pode ter SLA próprio
- Con: latência de rede (NATS round-trip ~1-5ms local)

## Decision
**IP Guard como produto standalone** (Opção B), integrado via NATS.

- Subject de request: `ipguard.license.verify` (Neotron → IP Guard)
- Subject de response: `ipguard.license.result` (IP Guard → Neotron)
- CLI: `neotron license verify <flake.nix>` publica no subject e aguarda reply (timeout: 10s)
- IP Guard tem seu próprio NixOS module (`nix/modules/ip-guard.nix`) — F1 do ROADMAP 1

Boundary: IP Guard **nunca** é importado como biblioteca Python — apenas comunicação NATS.

## Consequences
1. IP Guard pode ser atualizado/deployado sem rebuild de neotron ou owasaka
2. Neotron deve tolerar timeout gracefully: se IP Guard offline, `license verify` retorna `status: unavailable` (não falha hard)
3. Cache local (`neotron license status`) evita round-trips repetidos para o mesmo flake hash
4. IP Guard pode ser usado por outros repos do ecosistema (owasaka, spectre) sem dependência cruzada
5. NATS subject `ipguard.*` é reservado exclusivamente para IP Guard — não deve ser usado por outros serviços
