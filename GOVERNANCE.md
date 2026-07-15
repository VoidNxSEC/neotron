# NEXUS Governance — Tier Model

> **Status**: Accepted (ADR-0009)
> **Principle**: Every agent knows its tier. Every violation is logged, not silent. No tier escalates itself.

---

## Tier Hierarchy

```
Tier 0 — Constitutional   Human founders / architects
    │
Tier 1 — Council          Senior agents + human stakeholders
    │
Tier 2 — Operational      Registered active agents
    │
Tier 3 — Autonomous       Enforcement (SENTINEL, BASTION, CORTEX guards)
```

---

## Tier 0 — Constitutional

**Who**: Human key holders (hardware key / HSM recommended)
**Identity**: Ed25519 keypair held by humans, never by automated processes
**Authorities**:
- Accept/supersede ADRs
- Deploy or upgrade smart contracts
- Modify `flake.nix`, `foundry.toml`, `GOVERNANCE.md`
- Veto any Tier 1 DAO proposal before execution

**Constraints**:
- Cannot delegate Tier 0 authority to an agent
- All actions must be recorded as ADR entries

**Failure response**: Block + audit log + human notification (not silent, not automated rollback)

---

## Tier 1 — Council

**Who**: Agents with `tier = Council` registered in `IntelAgentDAO` + human stakeholders
**Identity**: Ed25519 NKey registered on-chain (wallet) + NATS NKey scoped to `council.*` subjects
**Authorities**:
- Create DAO proposals: `RegisterAgent`, `SlashAgent`, `UpdateParams`
- Vote on any proposal
- Propose ADR (requires Tier 0 pre-sign to accept)
- Mint reward via approved `MintReward` proposal

**Constraints**:
- Cannot override an accepted ADR without Tier 0 approval
- Minimum quorum: 50% of active Council agents (ceiling division)
- Timelock before execution

**Failure response**: Revert with typed error + emit `compliance.tier_violation.v1` to NATS (proportional — no crash, no flood)

---

## Tier 2 — Operational

**Who**: Active registered agents with `tier = Operational`
**Identity**: Ed25519 NKey scoped to `task.*` and `quality.*` NATS subjects only
**Authorities**:
- Publish `task.assigned.v1` (signed)
- Publish `quality.report.v1` (signed)
- Receive `GovernanceContext` on init (knows its own constraints)

**Constraints**:
- Cannot publish to `adr.*`, `council.*`, `dao.*` subjects
- Cannot create DAO proposals directly
- `quality.report.v1` is informational only — does NOT trigger on-chain mint automatically

**Failure response**: Reject message + emit warning event to `compliance.tier_violation.v1` (single event, not a flood)

---

## Tier 3 — Autonomous

**Who**: SENTINEL, BASTION, CORTEX guardrails
**Identity**: Service account — no governance keypair
**Authorities**:
- Enforce compliance rules defined by Tiers 0–1
- Block/allow actions at kernel or application layer
- Emit compliance events to NATS

**Constraints**:
- Zero discretion — only executes what rules specify
- Cannot initiate DAO proposals or ADRs
- Cannot modify its own rules

**Failure response**: Block action + structured log (never silent, never disproportionate — one log entry per event)

---

## Rules

1. **No self-elevation**: An agent cannot create a proposal that raises its own tier
2. **Signed payloads**: All NATS messages carry Ed25519 signature + sender tier
3. **Aware, not blind**: Every agent receives `GovernanceContext` at init — knows what it can and cannot do
4. **Proportional failures**: Violations produce one structured event, not silence and not cascading alerts
5. **NATS is informational**: No on-chain action is triggered automatically from a NATS message
6. **On-chain is authoritative**: DAO contract is the source of truth for tier, reputation, and decisions

---

## NATS Subject Map by Tier

| Subject | Publisher Tier | Subscriber |
|---------|---------------|------------|
| `adr.proposed.v1` | Tier 1 | Tier 0 (human review) |
| `adr.accepted.v1` | Tier 0 | All |
| `council.proposal.v1` | Tier 1 | Tier 1 |
| `task.assigned.v1` | Tier 2 | Tier 2, Tier 3 |
| `quality.report.v1` | Tier 2 | Tier 1 (inform council) |
| `compliance.tier_violation.v1` | Tier 3 | All (audit) |
| `neotron.compliance.sentinel.v1` | Tier 3 | Owasaka SIEM |

---

## Violation Response (Proportional Scale)

| Severity | Condition | Response |
|----------|-----------|----------|
| Info | Agent uses allowed subject | No action |
| Warning | Agent attempts subject outside tier | Reject + 1 NATS event |
| Error | Agent attempts proposal beyond tier | Contract revert + 1 audit log |
| Critical | Tier 0 key compromise suspected | Human notification only (not automated) |
