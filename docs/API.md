# NEXUS Platform API Reference

This document outlines the core public APIs for the NEXUS Platform.

## 🛡️ SENTINEL (Compliance)

### `ComplianceGuardrail`

The fundamental unit of enforcement.

```python
from neutron.compliance import ComplianceGuardrail, ValidationResult

def my_check(output: AgentOutput) -> ValidationResult:
    ...

guardrail = ComplianceGuardrail(
    name="check_pii",
    regulation="GDPR",
    check=my_check,
    severity="block"
)
```

### `AuditLogger`

Immutable logging interface.

```python
from neutron.compliance import AuditLogger

logger = AuditLogger()
log_id = logger.log(
    guardrail_name="check_pii",
    passed=True,
    details="No PII found"
)
```

## 🧠 CORTEX (Orchestration)

### `AgentSwarm`

Coordinates multiple agents to reach a consensus.

```python
from neutron.orchestration import AgentSwarm, Agent

swarm = AgentSwarm(
    agents=[agent_a, agent_b, agent_c],
    consensus_strategy="weighted_majority"
)

result = await swarm.execute(task)
```

### `ConsensusStrategy`

Enum of available strategies:
-   `MAJORITY_VOTE`
-   `UNANIMOUS`
-   `WEIGHTED_AVERAGE`
-   `BEST_CONFIDENCE`

## 🔌 SYNAPSE (Memory)

### `MemoryStore`

Vector-database backed long-term memory.

```python
from neutron.memory import MemoryStore

store = MemoryStore()
await store.add(text="User prefers dark mode", metadata={"user_id": "123"})

memories = await store.search("preference", limit=5)
```

## 🔮 ORACLE (Reasoning)

### `EnsembleReasoner`

Generates explanations using multiple strategies.

```python
from neutron.reasoning import EnsembleReasoner, ExplanationType

oracle = EnsembleReasoner()
explanation = await oracle.explain(
    decision=result,
    strategy=ExplanationType.CHAIN_OF_THOUGHT
)
```
