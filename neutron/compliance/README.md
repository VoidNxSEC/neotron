# SENTINEL - Compliance Guardrails as Code

**Enforce regulatory compliance at runtime for AI/ML agent outputs**

---

## Quick Start

```python
from neutron.compliance.auditors import lgpd_art18_explanation_guardrail
from neutron.compliance.sentinel import AgentOutput, ComplianceViolation

# Create agent output
output = AgentOutput(
    content="Loan approved for $50,000",
    has_explanation=True,
    explanation="Approved based on credit score 780, income $85k/year...",
    explanation_quality=0.85
)

# Enforce compliance
try:
    enforced = lgpd_art18_explanation_guardrail.enforce(output)
    print(f"✅ Compliant - Audit ID: {enforced.audit_id}")
except ComplianceViolation as e:
    print(f"❌ Blocked: {e.result.details}")
```

---

## Module Structure

```
neutron/compliance/
├── README.md                 # This file
├── __init__.py              # Package exports
├── sentinel.py              # Core guardrail engine
├── audit_logger.py          # Immutable audit trail
├── schema.sql               # PostgreSQL schema
└── auditors/                # Regulation-specific guardrails
    ├── __init__.py
    └── lgpd.py              # LGPD (Brazil) compliance
```

---

## Core Components

### 1. sentinel.py - Core Engine

**Classes:**
- `AgentOutput` - Agent output data model
- `ValidationResult` - Validation check result
- `ComplianceGuardrail` - Declarative guardrail
- `EnforcedOutput` - Wrapped output after enforcement
- `ComplianceViolation` - Exception for blocking violations

**Usage:**
```python
from neutron.compliance.sentinel import ComplianceGuardrail, AgentOutput, ValidationResult

def my_check(output: AgentOutput) -> ValidationResult:
    if meets_requirement(output):
        return ValidationResult(passed=True, details="OK")
    return ValidationResult(passed=False, details="Failed")

guardrail = ComplianceGuardrail(
    name="my_guardrail",
    regulation="LGPD",
    check=my_check,
    severity="block"  # or "warn", "audit"
)

enforced = guardrail.enforce(output)
```

### 2. audit_logger.py - Audit Trail

**Class:** `AuditLogger`

**Methods:**
- `log(audit_data)` - Write to audit trail (returns audit_id)
- `query_audits(...)` - Query audit logs
- `get_violations_summary(...)` - Get compliance statistics

**Usage:**
```python
from neutron.compliance.audit_logger import AuditLogger

logger = AuditLogger()

# Log event
audit_id = logger.log({
    "guardrail_name": "lgpd_art18_explanation",
    "regulation": "LGPD",
    "passed": True,
    # ... other fields
})

# Query violations
violations = logger.query_audits(
    regulation="LGPD",
    passed=False,
    limit=100
)
```

### 3. auditors/ - Regulation-Specific Guardrails

#### LGPD (Brazil)

**Pre-configured Guardrails:**
- `lgpd_art18_explanation_guardrail` - Right to Explanation (blocking)
- `lgpd_art20_portability_guardrail` - Data Portability (warning)

**Usage:**
```python
from neutron.compliance.auditors import (
    lgpd_art18_explanation_guardrail,
    get_lgpd_guardrails,
    validate_with_lgpd
)

# Single guardrail
enforced = lgpd_art18_explanation_guardrail.enforce(output)

# All LGPD guardrails
results = validate_with_lgpd(output)
```

---

## Workflow Integration

### Temporal Activities

```python
from neutron.orchestration.workflows import validate_agent_output_activity

# In your workflow
validation_result = await workflow.execute_activity(
    validate_agent_output_activity,
    args=[
        output_text,
        explanation,
        explanation_quality,
        metadata,
        model_name
    ],
    start_to_close_timeout=timedelta(seconds=30)
)

if not validation_result["passed"]:
    # Handle compliance violation
    workflow.logger.error(f"Blocked by: {validation_result['blocked_by']}")
```

---

## Database Schema

**Table:** `compliance_audits`

```sql
CREATE TABLE compliance_audits (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    guardrail_name VARCHAR(255) NOT NULL,
    regulation VARCHAR(50) NOT NULL,
    agent_output_hash VARCHAR(64) NOT NULL,
    validation_result JSONB NOT NULL,
    severity VARCHAR(20) NOT NULL,
    passed BOOLEAN NOT NULL,
    details TEXT,
    model_name VARCHAR(255)
);
```

**Views:**
- `compliance_violations` - Failed validations only
- `compliance_summary` - Aggregate statistics

---

## Testing

```bash
# Run all compliance tests
pytest tests/compliance/ -v

# Run specific test file
pytest tests/compliance/test_sentinel.py -v
pytest tests/compliance/auditors/test_lgpd.py -v
pytest tests/compliance/test_workflow_integration.py -v

# Run with coverage
pytest tests/compliance/ --cov=neutron.compliance --cov-report=html
```

---

## Documentation

- **Usage Guide:** `/docs/SENTINEL_USAGE.md` - How to use SENTINEL
- **Design Doc:** `/docs/SENTINEL_DESIGN.md` - Architecture details
- **Showcase:** `/docs/SENTINEL_SHOWCASE.md` - Business value & ROI
- **Guidelines:** `/docs/SENTINEL_GUIDELINES.md` - Production deployment
- **Demo Script:** `/scripts/demo_sentinel.py` - Live demonstrations

---

## Key Features

✅ **Runtime Enforcement** - Block non-compliant outputs before delivery
✅ **Immutable Audit Trail** - Write-only PostgreSQL logs
✅ **Regulation-Specific** - LGPD Article 18, 20 (GDPR, AI Act coming)
✅ **Declarative** - Compliance as code (version controlled)
✅ **Temporal Integration** - Native workflow activities
✅ **Production Ready** - HA, monitoring, CI/CD

---

## Roadmap

- **Phase 1 (Weeks 1-4):** ✅ LGPD + SENTINEL core
- **Phase 2 (Weeks 5-8):** GDPR + SYNAPSE memory
- **Phase 3 (Weeks 9-12):** AI Act + ORACLE reasoning
- **Phase 4 (Weeks 13-16):** SOC2 + Enterprise polish

---

## Support

- **Demo:** `python scripts/demo_sentinel.py`
- **Documentation:** `docs/SENTINEL_USAGE.md`
- **Issues:** GitHub Issues
- **Email:** `compliance@neutron.ai`

---

**Version:** 1.0 (Phase 1 Complete)
**Last Updated:** 2026-01-16
**Status:** Production Ready
