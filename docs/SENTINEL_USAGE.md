# SENTINEL Usage Guide

**Compliance Guardrails as Code for AI/ML Agents**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Using Pre-configured Guardrails](#using-pre-configured-guardrails)
4. [Creating Custom Guardrails](#creating-custom-guardrails)
5. [Integration with Workflows](#integration-with-workflows)
6. [Querying Audit Logs](#querying-audit-logs)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)

---

## Quick Start

### Installation

SENTINEL is included in the Neutron package:

```bash
# Install Neutron with all dependencies
poetry install

# Or with pip
pip install neutron
```

### Basic Usage

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

### Run Demo

```bash
# Run all demos
python scripts/demo_sentinel.py

# Run specific demo
python scripts/demo_sentinel.py --demo article18
```

---

## Core Concepts

### 1. AgentOutput

Represents output from an AI/ML agent that needs compliance validation:

```python
from neutron.compliance.sentinel import AgentOutput

output = AgentOutput(
    content="The main output text or data",
    has_explanation=True,
    explanation="Why this decision was made",
    explanation_quality=0.85,  # 0.0-1.0
    metadata={
        "exportable_format": "json",
        "data_structure": {...}
    },
    model_name="my-model-v1"
)
```

**Key Fields:**
- `content` (required): Main output text/data
- `has_explanation`: Whether explanation is provided (LGPD Art. 18)
- `explanation`: Human-readable explanation
- `explanation_quality`: Quality score (0.0-1.0, threshold: 0.7)
- `metadata`: Additional metadata (portability info for Art. 20)
- `model_name`: Name of model that generated output

### 2. ComplianceGuardrail

Declarative policy that enforces regulatory requirements:

```python
from neutron.compliance.sentinel import ComplianceGuardrail

guardrail = ComplianceGuardrail(
    name="my_guardrail",
    regulation="LGPD",  # LGPD, GDPR, AI_ACT, SOC2
    check=validation_function,
    severity="block",  # block, warn, audit
    description="What this guardrail checks"
)
```

**Severity Levels:**
- `block`: Raises ComplianceViolation (output rejected)
- `warn`: Logs violation but allows output
- `audit`: Logs event for monitoring only

### 3. ValidationResult

Result of a compliance check:

```python
from neutron.compliance.sentinel import ValidationResult

result = ValidationResult(
    passed=True,
    details="Human-readable explanation",
    confidence=0.9,
    metadata={"additional": "context"}
)
```

### 4. Immutable Audit Trail

Every enforcement is logged to PostgreSQL:

- **Write-only**: Logs cannot be modified or deleted
- **Cryptographic hashing**: SHA-256 for tamper detection
- **Indexed queries**: Fast retrieval by regulation, timestamp, etc.

---

## Using Pre-configured Guardrails

### LGPD Article 18 - Right to Explanation

**Requirement:** Automated decisions must have clear, adequate explanations.

**Usage:**

```python
from neutron.compliance.auditors import lgpd_art18_explanation_guardrail

output = AgentOutput(
    content="Loan denied",
    has_explanation=True,
    explanation=(
        "Denied based on: credit score below 650, "
        "debt-to-income ratio above 40%, and insufficient income."
    ),
    explanation_quality=0.82
)

try:
    enforced = lgpd_art18_explanation_guardrail.enforce(output)
    # Output passed - proceed
except ComplianceViolation as e:
    # Output blocked - must regenerate with explanation
    print(f"Blocked: {e.result.details}")
```

**Validation Checks:**
1. ✅ Explanation presence (`has_explanation=True`)
2. ✅ Explanation not empty
3. ✅ Quality score >= 0.7
4. ✅ Minimum length >= 20 characters

**Severity:** `block` (violations prevent output)

### LGPD Article 20 - Data Portability

**Requirement:** Data must be in machine-readable format for portability.

**Usage:**

```python
from neutron.compliance.auditors import lgpd_art20_portability_guardrail

output = AgentOutput(
    content='{"risk_score": 0.72, "risk_level": "HIGH"}',
    metadata={
        "exportable_format": "json",
        "data_structure": {
            "risk_score": "float",
            "risk_level": "string"
        }
    }
)

enforced = lgpd_art20_portability_guardrail.enforce(output)

if not enforced.validation_result.passed:
    print(f"Warning: {enforced.validation_result.details}")
else:
    print("Data is portable")
```

**Validation Checks:**
1. ✅ Metadata presence
2. ✅ Exportable format specified (JSON, CSV, XML, etc.)
3. ✅ Machine-readable format
4. ✅ Data structure documented

**Severity:** `warn` (violations logged but don't block)

### Get All LGPD Guardrails

```python
from neutron.compliance.auditors import get_lgpd_guardrails

guardrails = get_lgpd_guardrails()

for guardrail in guardrails:
    print(f"{guardrail.name}: {guardrail.severity}")
```

### Get Specific Guardrail by Article

```python
from neutron.compliance.auditors import get_lgpd_guardrail_by_article

# Get Article 18 guardrail
art18 = get_lgpd_guardrail_by_article(18)

# Get Article 20 guardrail
art20 = get_lgpd_guardrail_by_article(20)
```

### Batch Validation

```python
from neutron.compliance.auditors import validate_with_lgpd

output = AgentOutput(...)

# Validate against all LGPD guardrails
results = validate_with_lgpd(output)

for result in results:
    if result.passed:
        print(f"✅ {result.details}")
    else:
        print(f"❌ {result.details}")
```

---

## Creating Custom Guardrails

### Step 1: Define Validation Function

```python
from neutron.compliance.sentinel import AgentOutput, ValidationResult

def check_custom_requirement(output: AgentOutput) -> ValidationResult:
    """
    Custom validation logic

    Returns:
        ValidationResult with pass/fail status
    """
    # Your validation logic
    if meets_requirement(output):
        return ValidationResult(
            passed=True,
            details="Requirement met",
            confidence=1.0
        )
    else:
        return ValidationResult(
            passed=False,
            details="Requirement not met: specific reason",
            confidence=1.0,
            metadata={"violation_type": "custom_violation"}
        )
```

### Step 2: Create Guardrail

```python
from neutron.compliance.sentinel import ComplianceGuardrail

custom_guardrail = ComplianceGuardrail(
    name="custom_requirement",
    regulation="SOC2",  # or LGPD, GDPR, AI_ACT
    check=check_custom_requirement,
    severity="block",  # or "warn", "audit"
    description="Ensures custom requirement is met"
)
```

### Step 3: Enforce Guardrail

```python
output = AgentOutput(...)

try:
    enforced = custom_guardrail.enforce(output)
    print(f"Passed - Audit ID: {enforced.audit_id}")
except ComplianceViolation as e:
    print(f"Blocked: {e.result.details}")
```

### Example: Custom PII Detection

```python
import re

def check_no_pii(output: AgentOutput) -> ValidationResult:
    """Ensure output doesn't contain PII (email, phone, SSN)"""

    # Patterns for PII
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'

    found_pii = []

    if re.search(email_pattern, output.content):
        found_pii.append("email address")
    if re.search(phone_pattern, output.content):
        found_pii.append("phone number")
    if re.search(ssn_pattern, output.content):
        found_pii.append("SSN")

    if found_pii:
        return ValidationResult(
            passed=False,
            details=f"PII detected: {', '.join(found_pii)}",
            confidence=0.9,
            metadata={"pii_types": found_pii}
        )

    return ValidationResult(
        passed=True,
        details="No PII detected",
        confidence=0.9
    )

# Create guardrail
no_pii_guardrail = ComplianceGuardrail(
    name="no_pii_in_output",
    regulation="GDPR",
    check=check_no_pii,
    severity="block",
    description="Prevents PII leakage in agent outputs"
)
```

---

## Integration with Workflows

### Temporal Workflow Integration

SENTINEL provides Temporal activities for seamless integration:

```python
from neutron.orchestration.workflows import (
    validate_agent_output_activity,
    batch_validate_outputs_activity
)
from temporalio import workflow

@workflow.defn(name="MyMLWorkflow")
class MyMLWorkflow:
    @workflow.run
    async def run(self, task: dict) -> dict:
        # Generate output
        output_text = await self.generate_output(task)
        explanation = await self.explain_output(output_text)

        # Validate with SENTINEL
        validation_result = await workflow.execute_activity(
            validate_agent_output_activity,
            args=[output_text, explanation, 0.85],
            start_to_close_timeout=timedelta(seconds=30)
        )

        if not validation_result["passed"]:
            # Output blocked - log and retry
            workflow.logger.error(f"Blocked: {validation_result['blocked_by']}")

            # Regenerate with better explanation
            improved_output = await self.regenerate_with_explanation(task)
            # ... retry validation

        return validation_result
```

### Activity Parameters

```python
await validate_agent_output_activity(
    output_text="Agent output text",
    explanation="Why this decision was made",
    explanation_quality=0.85,
    metadata={
        "exportable_format": "json",
        "data_structure": {...}
    },
    model_name="my-model-v1",
    guardrails=["lgpd_art18_explanation"]  # Optional: specific guardrails
)
```

### Batch Validation in Workflows

```python
# Validate ensemble outputs
ensemble_outputs = [
    {"output_text": "Model A result", "explanation": "...", ...},
    {"output_text": "Model B result", "explanation": "...", ...},
    {"output_text": "Model C result", "explanation": "...", ...}
]

results = await workflow.execute_activity(
    batch_validate_outputs_activity,
    args=[ensemble_outputs],
    start_to_close_timeout=timedelta(seconds=60)
)

# Filter to compliant models only
compliant = [r for r in results if r["passed"]]
# Use compliant models for consensus
```

---

## Querying Audit Logs

### Basic Query

```python
from neutron.compliance.audit_logger import AuditLogger

logger = AuditLogger()

# Get recent audits
audits = logger.query_audits(
    regulation="LGPD",
    limit=100
)

for audit in audits:
    print(f"{audit['timestamp']}: {audit['guardrail_name']} - {'PASSED' if audit['passed'] else 'FAILED'}")
```

### Query Violations Only

```python
# Get all violations
violations = logger.query_audits(
    regulation="LGPD",
    passed=False,
    limit=50
)

for violation in violations:
    print(f"❌ {violation['guardrail_name']}")
    print(f"   {violation['details']}")
    print(f"   {violation['timestamp']}")
```

### Filter by Guardrail

```python
# Get audits for specific guardrail
art18_audits = logger.query_audits(
    guardrail_name="lgpd_art18_explanation",
    limit=100
)
```

### Filter by Time Range

```python
from datetime import datetime, timedelta

# Last 7 days
start_time = datetime.utcnow() - timedelta(days=7)

audits = logger.query_audits(
    regulation="LGPD",
    start_time=start_time,
    limit=1000
)
```

### Get Compliance Summary

```python
# Get summary statistics
summary = logger.get_violations_summary(
    regulation="LGPD",
    days_back=30
)

print(f"Total audits: {summary['total_audits']}")
print(f"Violations: {summary['total_violations']}")
print(f"Compliance rate: {summary['compliance_rate']:.1%}")
print(f"Top violations: {summary['top_violations']}")
```

### Direct SQL Queries

```python
# For advanced reporting, query PostgreSQL directly
import psycopg2

conn = psycopg2.connect("your_connection_string")
cursor = conn.cursor()

# Custom query
cursor.execute("""
    SELECT
        DATE(timestamp) as date,
        COUNT(*) as total_audits,
        SUM(CASE WHEN passed = false THEN 1 ELSE 0 END) as violations
    FROM compliance_audits
    WHERE regulation = 'LGPD'
      AND timestamp >= NOW() - INTERVAL '30 days'
    GROUP BY DATE(timestamp)
    ORDER BY date DESC
""")

for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} audits, {row[2]} violations")
```

---

## Best Practices

### 1. Always Validate Agent Outputs

```python
# ✅ Good: Validate every output
output = agent.generate(task)
enforced = guardrail.enforce(output)
deliver_to_user(enforced.original.content)

# ❌ Bad: Skip validation
output = agent.generate(task)
deliver_to_user(output.content)  # No compliance check!
```

### 2. Handle Violations Gracefully

```python
# ✅ Good: Handle violations and retry
try:
    enforced = guardrail.enforce(output)
except ComplianceViolation as e:
    # Log violation
    logger.error(f"Compliance violation: {e.guardrail.name}")

    # Regenerate with better explanation
    improved_output = agent.regenerate_with_explanation(task)
    enforced = guardrail.enforce(improved_output)

# ❌ Bad: Ignore violations
try:
    enforced = guardrail.enforce(output)
except ComplianceViolation:
    pass  # Silently ignore violation - BAD!
```

### 3. Use Appropriate Severity Levels

```python
# Critical requirements (e.g., LGPD Art. 18): block
critical_guardrail = ComplianceGuardrail(
    severity="block"  # Must pass
)

# Nice-to-have (e.g., data portability): warn
optional_guardrail = ComplianceGuardrail(
    severity="warn"  # Log but don't block
)

# Monitoring only: audit
monitoring_guardrail = ComplianceGuardrail(
    severity="audit"  # Just log for analytics
)
```

### 4. Provide Quality Explanations

```python
# ✅ Good: Detailed, specific explanation
output = AgentOutput(
    content="Loan approved",
    explanation=(
        "Approved based on: credit score 780 (excellent), "
        "income $85k/year (sufficient), DTI 22% (low), "
        "no late payments (24 months), employment 5 years."
    ),
    explanation_quality=0.88
)

# ❌ Bad: Vague explanation
output = AgentOutput(
    content="Loan approved",
    explanation="Looks good.",
    explanation_quality=0.3
)
```

### 5. Include Portability Metadata

```python
# ✅ Good: Include exportable format
output = AgentOutput(
    content='{"risk": 0.72}',
    metadata={
        "exportable_format": "json",
        "data_structure": {
            "risk": "float (0.0-1.0)"
        }
    }
)

# ⚠️ Warning: No portability info
output = AgentOutput(
    content='{"risk": 0.72}',
    metadata=None  # Will trigger Article 20 warning
)
```

### 6. Monitor Compliance Metrics

```python
# Regularly check compliance rates
summary = logger.get_violations_summary("LGPD", days_back=7)

if summary["compliance_rate"] < 0.95:
    # Alert team if compliance rate drops
    send_alert(f"LGPD compliance at {summary['compliance_rate']:.1%}")
```

### 7. Test Guardrails Thoroughly

```python
import pytest

def test_custom_guardrail():
    """Test custom guardrail with various inputs"""

    # Test passing case
    compliant = AgentOutput(...)
    enforced = guardrail.enforce(compliant)
    assert enforced.validation_result.passed

    # Test failing case
    non_compliant = AgentOutput(...)
    with pytest.raises(ComplianceViolation):
        guardrail.enforce(non_compliant)
```

---

## Troubleshooting

### Issue: Database Connection Error

**Symptom:**
```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Apply schema
./scripts/setup_compliance_db.sh

# Verify
docker-compose exec postgres psql -U neutron -d neutron -c '\dt compliance*'
```

### Issue: All Outputs Failing Validation

**Symptom:** Every output gets blocked

**Solution:**
1. Check explanation quality score (must be >= 0.7)
2. Ensure explanation is not empty
3. Verify explanation length (>= 20 characters)

```python
# Debug validation
output = AgentOutput(...)
result = lgpd_art18_explanation_guardrail.check(output)
print(f"Passed: {result.passed}")
print(f"Details: {result.details}")
print(f"Metadata: {result.metadata}")
```

### Issue: Audit Logs Not Created

**Symptom:** `query_audits()` returns empty list

**Solution:**
1. Check database connection string
2. Verify schema is applied
3. Ensure guardrail.enforce() was called (not just check())

```python
# Verify audit logging
enforced = guardrail.enforce(output)
print(f"Audit ID: {enforced.audit_id}")  # Should be integer

# Query by audit ID
audit = logger.get_audit_by_id(enforced.audit_id)
print(audit)
```

### Issue: "Module not found" Error

**Symptom:**
```
ModuleNotFoundError: No module named 'neutron.compliance'
```

**Solution:**
```bash
# Reinstall package
poetry install

# Or with pip
pip install -e .

# Verify installation
python -c "from neutron.compliance.sentinel import AgentOutput; print('✅ OK')"
```

---

## API Reference

### AgentOutput

```python
@dataclass
class AgentOutput:
    content: str
    metadata: Optional[dict] = None
    has_explanation: bool = False
    explanation: Optional[str] = None
    explanation_quality: float = 0.0
    model_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

### ComplianceGuardrail

```python
@dataclass
class ComplianceGuardrail:
    name: str
    regulation: Literal["LGPD", "GDPR", "AI_ACT", "SOC2"]
    check: Callable[[AgentOutput], ValidationResult]
    severity: Literal["block", "warn", "audit"]
    description: str = ""
    enabled: bool = True

    def enforce(self, output: AgentOutput) -> EnforcedOutput:
        """Enforce guardrail on output"""

    def disable(self):
        """Disable this guardrail"""

    def enable(self):
        """Enable this guardrail"""
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    passed: bool
    details: str
    confidence: float = 1.0
    metadata: Optional[dict] = None
```

### AuditLogger

```python
class AuditLogger:
    def log(self, audit_data: dict) -> int:
        """Log audit event, returns audit_id"""

    def query_audits(
        self,
        guardrail_name: str = None,
        regulation: str = None,
        passed: bool = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[dict]:
        """Query audit logs"""

    def get_violations_summary(
        self,
        regulation: str = None,
        days_back: int = 7
    ) -> dict:
        """Get violation summary statistics"""
```

### LGPD Auditors

```python
# Pre-configured guardrails
lgpd_art18_explanation_guardrail: ComplianceGuardrail
lgpd_art20_portability_guardrail: ComplianceGuardrail
LGPD_GUARDRAILS: List[ComplianceGuardrail]

# Convenience functions
def get_lgpd_guardrails() -> List[ComplianceGuardrail]:
    """Get all LGPD guardrails"""

def get_lgpd_guardrail_by_article(article_number: int) -> ComplianceGuardrail:
    """Get guardrail by article number (18 or 20)"""

def validate_with_lgpd(output: AgentOutput) -> List[ValidationResult]:
    """Batch validate against all LGPD guardrails"""
```

---

## Additional Resources

- [SENTINEL Design Document](./SENTINEL_DESIGN.md) - Architecture details
- [LGPD Full Text](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [Week 3 Completion Report](../WEEK3_COMPLETE.md) - Implementation details
- [Demo Script](../scripts/demo_sentinel.py) - Working examples

---

**Document Version**: 1.0
**Last Updated**: 2026-01-16
**Status**: Week 4 - Production Ready
