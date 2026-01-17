# SENTINEL Design Document
**Compliance Guardrails as Code**

---

## Overview

SENTINEL is the first pillar of NEXUS - a declarative compliance guardrail system that ENFORCES regulatory requirements at runtime, not just suggests them.

**Philosophy**: Compliance is not optional. Every AI agent decision must be validated against regulatory requirements, and every validation must be logged to an immutable audit trail.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Output Flow                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Agent → AgentOutput → ComplianceGuardrail → EnforcedOutput │
│                              │                               │
│                              ├──> [PASS] → Return Output     │
│                              │                               │
│                              ├──> [FAIL + block] → Raise     │
│                              │    ComplianceViolation        │
│                              │                               │
│                              └──> [FAIL + warn/audit] →      │
│                                   Log & Return               │
│                                                              │
│         Every enforcement logged to immutable                │
│         PostgreSQL audit trail                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. ComplianceGuardrail

The central abstraction. A guardrail is:
- **Declarative**: Defined as code, not configuration
- **Regulation-Specific**: Tied to LGPD, GDPR, AI Act, or SOC2
- **Enforced**: Not suggestions - violations are blocked
- **Audited**: Every enforcement logged immutably

```python
@dataclass
class ComplianceGuardrail:
    name: str                    # Unique identifier
    regulation: Literal[...]     # LGPD, GDPR, AI_ACT, SOC2
    check: Callable              # Validation function
    severity: Literal[...]       # block, warn, audit
    description: str = ""
    enabled: bool = True
```

**Severity Levels:**

| Severity | Behavior | Use Case |
|----------|----------|----------|
| `block` | Raises ComplianceViolation | Critical violations (LGPD Art. 18) |
| `warn` | Logs violation, returns output | Non-critical violations |
| `audit` | Logs event for compliance tracking | Monitoring only |

### 2. AgentOutput

Standardized representation of AI agent outputs:

```python
@dataclass
class AgentOutput:
    content: str                      # Main output
    metadata: Optional[dict]          # Additional context
    has_explanation: bool = False     # LGPD Art. 18 requirement
    explanation: Optional[str]        # Human-readable explanation
    explanation_quality: float = 0.0  # Quality score (0-1)
    model_name: Optional[str]         # Which model generated this
    timestamp: datetime               # When it was generated
```

**Key Fields:**
- `has_explanation` + `explanation`: Required for LGPD Article 18
- `explanation_quality`: Computed score for explanation adequacy
- `model_name`: For tracking which models are compliant

### 3. ValidationResult

Result of a compliance check:

```python
@dataclass
class ValidationResult:
    passed: bool          # Did it pass?
    details: str          # Human-readable explanation
    confidence: float     # Confidence in validation (0-1)
    metadata: Optional[dict]  # Additional context
```

### 4. AuditLogger

Immutable audit trail using PostgreSQL:

**Key Features:**
- **Write-Only**: Logs cannot be modified or deleted
- **Cryptographic Hashing**: SHA-256 hash of outputs for tamper detection
- **Indexed Queries**: Fast retrieval by regulation, guardrail, timestamp
- **Integrity Verification**: Detect gaps in audit logs

```python
class AuditLogger:
    def log(self, audit_data: Dict) -> int:
        # Logs to PostgreSQL, returns audit_id

    def query_audits(
        self,
        guardrail_name: str = None,
        regulation: str = None,
        passed: bool = None,
        limit: int = 100
    ) -> List[Dict]:
        # Read-only queries

    def get_violations_summary(
        self,
        regulation: str = None,
        days_back: int = 7
    ) -> Dict:
        # Aggregated statistics
```

---

## Database Schema

### compliance_audits Table

```sql
CREATE TABLE compliance_audits (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    guardrail_name VARCHAR(255) NOT NULL,
    regulation VARCHAR(50) NOT NULL,
    agent_output_hash VARCHAR(64) NOT NULL,  -- SHA-256
    validation_result JSONB NOT NULL,
    severity VARCHAR(20) NOT NULL,
    passed BOOLEAN NOT NULL,
    details TEXT,
    model_name VARCHAR(255)
);
```

**Immutability Guarantees:**
1. No UPDATE or DELETE permissions on production
2. Append-only audit trail
3. Cryptographic hashing for tamper detection
4. Sequential IDs detect missing records

**Views:**
- `compliance_violations`: Quick view of all violations
- `compliance_summary`: Aggregated stats by regulation

---

## Enforcement Flow

### 1. Agent Produces Output
```python
output = AgentOutput(
    content="Loan approved for $50,000",
    has_explanation=True,
    explanation="Approved based on: credit score 780, income $85k/year, no late payments",
    explanation_quality=0.85
)
```

### 2. Guardrail Validates
```python
guardrail = ComplianceGuardrail(
    name="lgpd_art18_explanation",
    regulation="LGPD",
    check=check_lgpd_explanation,
    severity="block"
)

enforced = guardrail.enforce(output)
```

### 3. Check Function Executes
```python
def check_lgpd_explanation(output: AgentOutput) -> ValidationResult:
    if not output.has_explanation:
        return ValidationResult(False, "No explanation provided")

    if output.explanation_quality < 0.7:
        return ValidationResult(False, f"Explanation quality too low: {output.explanation_quality}")

    return ValidationResult(True, "Adequate explanation provided")
```

### 4. Enforcement Based on Severity

**If severity="block" and validation fails:**
```python
raise ComplianceViolation(guardrail, result, output)
# Output is BLOCKED - agent must regenerate
```

**If severity="warn" and validation fails:**
```python
# Log violation but allow output through
enforced = EnforcedOutput(
    original=output,
    validation_result=result,
    enforced=True
)
return enforced
```

### 5. Audit Logging (Always)
```python
# Every enforcement logged to PostgreSQL
audit_id = audit_logger.log({
    "timestamp": now(),
    "guardrail_name": "lgpd_art18_explanation",
    "regulation": "LGPD",
    "agent_output_hash": sha256(output),
    "validation_result": result,
    "severity": "block",
    "passed": result.passed
})
```

---

## Integration with NEXUS

### With Temporal Workflows

```python
# In neutron/orchestration/workflows.py

@activity.defn(name="validate_agent_output")
async def validate_agent_output_activity(
    output_text: str,
    explanation: str,
    explanation_quality: float,
    guardrails: List[str]
) -> dict:
    """
    Validate agent output against compliance guardrails
    """
    output = AgentOutput(
        content=output_text,
        has_explanation=bool(explanation),
        explanation=explanation,
        explanation_quality=explanation_quality
    )

    for guardrail_name in guardrails:
        guardrail = get_guardrail(guardrail_name)

        try:
            enforced = guardrail.enforce(output)
        except ComplianceViolation as e:
            return {
                "passed": False,
                "error": str(e),
                "guardrail": e.guardrail.name
            }

    return {
        "passed": True,
        "output": output.content
    }
```

### With CORTEX (Multi-Agent)

```python
# Each agent output validated before consensus
@workflow.defn
class AgentCoordinationWorkflow:
    async def run(self, task: ComplexTask) -> AgentConsensus:
        # Get results from multiple agents
        results = await self.run_agents(task)

        # Validate each result with guardrails
        validated_results = []
        for result in results:
            try:
                enforced = self.validate_with_sentinel(result)
                validated_results.append(enforced)
            except ComplianceViolation:
                # Agent result blocked - exclude from consensus
                continue

        # Consensus only on compliant outputs
        return self.compute_consensus(validated_results)
```

---

## Security & Privacy Considerations

### 1. Output Hashing
- SHA-256 hash prevents audit trail tampering
- Hash stored separately from full output (privacy)
- Can verify output matches audit record

### 2. LGPD Compliance
- Audit logs contain only hashes + metadata
- Full outputs not stored (unless required by regulation)
- Right to explanation enforced at runtime

### 3. Access Control
- Audit logs read-only in production
- Separate database roles for audit vs. operational data
- Compliance team has read-only access

### 4. Data Retention
- Audit logs retained per regulatory requirements
- Default: 7 years (LGPD/GDPR standard)
- Configurable retention policies per regulation

---

## Performance Considerations

### 1. Validation Performance
- Check functions should be <100ms
- Async checks supported for expensive validations
- Caching for repeated validations

### 2. Audit Logging Performance
- Async logging to avoid blocking
- Batched inserts for high-throughput scenarios
- PostgreSQL connection pooling

### 3. Query Performance
- Indexes on common query patterns
- Materialized views for aggregated statistics
- Partition tables by timestamp for large datasets

---

## Extension Points

### 1. Custom Guardrails
```python
def check_custom_requirement(output: AgentOutput) -> ValidationResult:
    # Your custom validation logic
    if meets_requirement(output):
        return ValidationResult(True, "Custom check passed")
    return ValidationResult(False, "Custom check failed")

custom_guardrail = ComplianceGuardrail(
    name="custom_check",
    regulation="SOC2",
    check=check_custom_requirement,
    severity="warn"
)
```

### 2. Plugin System (Future)
```python
class GuardrailPlugin(Protocol):
    def register_checks(self) -> List[ComplianceGuardrail]:
        ...

    def pre_enforce(self, output: AgentOutput) -> AgentOutput:
        ...

    def post_enforce(self, enforced: EnforcedOutput) -> EnforcedOutput:
        ...
```

### 3. External Validation Services
```python
# Call external API for validation
async def check_external_service(output: AgentOutput) -> ValidationResult:
    response = await http_client.post(
        "https://compliance-api.example.com/validate",
        json={"content": output.content}
    )
    return ValidationResult(
        passed=response.json()["compliant"],
        details=response.json()["reason"]
    )
```

---

## Testing Strategy

### 1. Unit Tests
- Test each guardrail in isolation
- Test all severity levels (block, warn, audit)
- Test enable/disable functionality
- Test hashing consistency

### 2. Integration Tests
- Test with Temporal workflows
- Test with PostgreSQL
- Test audit trail integrity

### 3. Load Tests
- 1000+ validations/second
- Audit log write throughput
- Query performance under load

### 4. Compliance Tests
- Verify LGPD requirements met
- Verify GDPR requirements met
- Verify audit trail completeness

---

## Roadmap

### Phase 1 (Current - Week 1-4)
- ✅ Core guardrail engine
- ✅ Immutable audit logging
- ✅ PostgreSQL schema
- 🔄 LGPD auditors (Week 3)
- 🔄 Demo application (Week 4)

### Phase 2 (Week 5-8)
- GDPR auditors
- Integration with CORTEX multi-agent
- Real-time compliance dashboard

### Phase 3 (Week 9-12)
- AI Act auditors
- SOC2 auditors
- Cross-regulation conflict detection

### Phase 4 (Week 13-16)
- Compliance analytics
- Automated reporting
- Series A demo

---

## References

### Regulations
- [LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) - Lei Geral de Proteção de Dados (Brazil)
- [GDPR](https://gdpr-info.eu/) - General Data Protection Regulation (EU)
- [EU AI Act](https://artificialintelligenceact.eu/) - EU Artificial Intelligence Act
- [SOC2](https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/aicpasoc2report.html) - Service Organization Control 2

### Technical Inspiration
- [Open Policy Agent (OPA)](https://www.openpolicyagent.org/) - Policy as code
- [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) - LLM guardrails
- [Guardrails AI](https://www.guardrailsai.com/) - ML guardrails

---

## Appendix: Example Guardrails

### LGPD Article 18 - Right to Explanation
```python
def check_lgpd_article_18(output: AgentOutput) -> ValidationResult:
    """
    LGPD Article 18: Right to review automated decisions

    Requires:
    - Explanation present
    - Explanation quality > 0.7
    """
    if not output.has_explanation:
        return ValidationResult(
            passed=False,
            details="No explanation provided (LGPD Art. 18 violation)",
            confidence=1.0
        )

    if output.explanation_quality < 0.7:
        return ValidationResult(
            passed=False,
            details=f"Explanation quality insufficient: {output.explanation_quality:.2f} < 0.70",
            confidence=output.explanation_quality
        )

    return ValidationResult(
        passed=True,
        details=f"Adequate explanation provided (quality: {output.explanation_quality:.2f})",
        confidence=1.0
    )

lgpd_art18_guardrail = ComplianceGuardrail(
    name="lgpd_art18_explanation",
    regulation="LGPD",
    check=check_lgpd_article_18,
    severity="block",
    description="Ensures automated decisions have adequate explanations per LGPD Article 18"
)
```

### GDPR Article 22 - Automated Decision-Making
```python
def check_gdpr_article_22(output: AgentOutput) -> ValidationResult:
    """
    GDPR Article 22: Right not to be subject to automated decision-making

    Requires:
    - Human review flag if decision affects rights
    """
    if output.metadata and output.metadata.get("affects_rights"):
        if not output.metadata.get("human_review_required"):
            return ValidationResult(
                passed=False,
                details="Automated decision affecting rights requires human review (GDPR Art. 22)",
                confidence=1.0
            )

    return ValidationResult(
        passed=True,
        details="GDPR Article 22 requirements met",
        confidence=1.0
    )

gdpr_art22_guardrail = ComplianceGuardrail(
    name="gdpr_art22_automated_decision",
    regulation="GDPR",
    check=check_gdpr_article_22,
    severity="block",
    description="Ensures automated decisions comply with GDPR Article 22"
)
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-16
**Status**: Implementation Complete (Week 1)
