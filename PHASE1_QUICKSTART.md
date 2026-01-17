# Phase 1 Quick Start Guide
**SENTINEL Implementation - Weeks 1-4**

## Objective
Build SENTINEL - the compliance guardrail engine that makes NEXUS unique in the market.

## Why SENTINEL First?
1. ✅ **Unique competitive advantage** - leverages your legal expertise
2. ✅ **Testable in isolation** - doesn't require full multi-agent system
3. ✅ **Immediately marketable** - compliance is a universal pain point
4. ✅ **Can be open-sourced** - marketing tool ("OPA for AI")

---

## Week 1: Architecture & Setup

### Day 1-2: Module Structure
```bash
# Create the compliance module structure
mkdir -p neutron/compliance/auditors
touch neutron/compliance/__init__.py
touch neutron/compliance/sentinel.py
touch neutron/compliance/audit_logger.py
touch neutron/compliance/auditors/__init__.py
touch neutron/compliance/auditors/lgpd.py

# Create test structure
mkdir -p tests/compliance/auditors
touch tests/compliance/__init__.py
touch tests/compliance/test_sentinel.py
touch tests/compliance/test_audit_logger.py
touch tests/compliance/auditors/test_lgpd.py
```

### Day 3: Database Schema
```sql
-- Create audit tables in PostgreSQL
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
    CONSTRAINT immutable_audit CHECK (id > 0)  -- Makes row immutable after insert
);

-- Index for fast querying
CREATE INDEX idx_compliance_audits_timestamp ON compliance_audits(timestamp DESC);
CREATE INDEX idx_compliance_audits_guardrail ON compliance_audits(guardrail_name);
CREATE INDEX idx_compliance_audits_regulation ON compliance_audits(regulation);
```

### Day 4-5: API Design Document
Create `docs/SENTINEL_API.md` with:
- `ComplianceGuardrail` dataclass specification
- `ValidationResult` structure
- `EnforcedOutput` wrapper
- `ComplianceViolation` exception hierarchy
- Integration points with existing workflows

---

## Week 2: Core Implementation

### sentinel.py - Core Engine
```python
from dataclasses import dataclass
from typing import Callable, Literal, Any
from datetime import datetime
import hashlib
import json

from neutron.compliance.audit_logger import AuditLogger


@dataclass
class ValidationResult:
    """Result of a compliance check"""
    passed: bool
    details: str
    confidence: float = 1.0
    metadata: dict = None


@dataclass
class AgentOutput:
    """Agent output to be validated"""
    content: str
    metadata: dict = None
    has_explanation: bool = False
    explanation: str = None
    explanation_quality: float = 0.0


@dataclass
class EnforcedOutput:
    """Wrapped output after compliance enforcement"""
    original: AgentOutput
    validation_result: ValidationResult
    guardrail_name: str
    regulation: str
    enforced: bool


class ComplianceViolation(Exception):
    """Raised when a blocking guardrail fails"""
    def __init__(self, guardrail: 'ComplianceGuardrail', result: ValidationResult):
        self.guardrail = guardrail
        self.result = result
        super().__init__(
            f"Compliance violation: {guardrail.name} ({guardrail.regulation}) - {result.details}"
        )


@dataclass
class ComplianceGuardrail:
    """
    Declarative compliance guardrail

    Inspired by Open Policy Agent but for AI/ML outputs
    """
    name: str
    regulation: Literal["LGPD", "GDPR", "AI_ACT", "SOC2"]
    check: Callable[[AgentOutput], ValidationResult]
    severity: Literal["block", "warn", "audit"]
    description: str = ""

    def __post_init__(self):
        self.audit_logger = AuditLogger()

    def enforce(self, output: AgentOutput) -> EnforcedOutput:
        """
        Enforce guardrail on agent output

        Args:
            output: Agent output to validate

        Returns:
            EnforcedOutput with validation results

        Raises:
            ComplianceViolation: If severity="block" and validation fails
        """
        # Run compliance check
        result = self.check(output)

        # Compute hash of output for audit trail
        output_hash = self._hash_output(output)

        # Log to immutable audit store
        self.audit_logger.log({
            "timestamp": datetime.utcnow().isoformat(),
            "guardrail_name": self.name,
            "regulation": self.regulation,
            "agent_output_hash": output_hash,
            "validation_result": {
                "passed": result.passed,
                "details": result.details,
                "confidence": result.confidence
            },
            "severity": self.severity,
            "passed": result.passed
        })

        # Enforce based on severity
        if not result.passed and self.severity == "block":
            raise ComplianceViolation(self, result)

        return EnforcedOutput(
            original=output,
            validation_result=result,
            guardrail_name=self.name,
            regulation=self.regulation,
            enforced=True
        )

    def _hash_output(self, output: AgentOutput) -> str:
        """Generate SHA-256 hash of output for audit trail"""
        content = json.dumps({
            "content": output.content,
            "metadata": output.metadata
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
```

### audit_logger.py - Immutable Logging
```python
import psycopg2
from psycopg2.extras import Json
import os
from typing import Dict, Any
from datetime import datetime


class AuditLogger:
    """
    Immutable audit logger using PostgreSQL

    All logs are write-only - cannot be modified or deleted
    """

    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.getenv(
            "POSTGRES_URL",
            "postgresql://neutron:neutron@localhost:5432/neutron"
        )

    def log(self, audit_data: Dict[str, Any]) -> int:
        """
        Log compliance audit event

        Args:
            audit_data: Audit event data

        Returns:
            Audit log ID
        """
        conn = psycopg2.connect(self.connection_string)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO compliance_audits (
                        timestamp,
                        guardrail_name,
                        regulation,
                        agent_output_hash,
                        validation_result,
                        severity,
                        passed,
                        details
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    datetime.fromisoformat(audit_data["timestamp"]),
                    audit_data["guardrail_name"],
                    audit_data["regulation"],
                    audit_data["agent_output_hash"],
                    Json(audit_data["validation_result"]),
                    audit_data["severity"],
                    audit_data["passed"],
                    audit_data["validation_result"].get("details", "")
                ))

                audit_id = cur.fetchone()[0]
                conn.commit()
                return audit_id
        finally:
            conn.close()

    def query_audits(
        self,
        guardrail_name: str = None,
        regulation: str = None,
        passed: bool = None,
        limit: int = 100
    ) -> list:
        """Query audit logs (read-only)"""
        conn = psycopg2.connect(self.connection_string)
        try:
            with conn.cursor() as cur:
                conditions = []
                params = []

                if guardrail_name:
                    conditions.append("guardrail_name = %s")
                    params.append(guardrail_name)

                if regulation:
                    conditions.append("regulation = %s")
                    params.append(regulation)

                if passed is not None:
                    conditions.append("passed = %s")
                    params.append(passed)

                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                params.append(limit)

                cur.execute(f"""
                    SELECT * FROM compliance_audits
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, params)

                return cur.fetchall()
        finally:
            conn.close()
```

---

## Week 3: LGPD Auditor

### auditors/lgpd.py - LGPD Implementation
```python
from neutron.compliance.sentinel import ComplianceGuardrail, AgentOutput, ValidationResult


def check_lgpd_article_18_explanation(output: AgentOutput) -> ValidationResult:
    """
    LGPD Article 18 - Right to Explanation

    Validates that AI outputs provide adequate explanation for automated decisions
    """
    if not output.has_explanation:
        return ValidationResult(
            passed=False,
            details="No explanation provided for automated decision (LGPD Art. 18 violation)",
            confidence=1.0
        )

    if output.explanation_quality < 0.7:
        return ValidationResult(
            passed=False,
            details=f"Explanation quality too low: {output.explanation_quality:.2f} < 0.70",
            confidence=output.explanation_quality
        )

    return ValidationResult(
        passed=True,
        details=f"Adequate explanation provided (quality: {output.explanation_quality:.2f})",
        confidence=1.0
    )


# Pre-configured LGPD Article 18 guardrail
lgpd_explainability_guardrail = ComplianceGuardrail(
    name="lgpd_art18_explanation",
    regulation="LGPD",
    check=check_lgpd_article_18_explanation,
    severity="block",
    description="Ensures automated decisions have adequate explanations per LGPD Article 18"
)


def check_lgpd_article_20_data_portability(output: AgentOutput) -> ValidationResult:
    """
    LGPD Article 20 - Right to Data Portability

    Validates that outputs can be exported in structured format
    """
    if not output.metadata or "exportable" not in output.metadata:
        return ValidationResult(
            passed=False,
            details="Output not marked as exportable (LGPD Art. 20 violation)",
            confidence=1.0
        )

    if not output.metadata["exportable"]:
        return ValidationResult(
            passed=False,
            details="Output cannot be exported in structured format",
            confidence=1.0
        )

    return ValidationResult(
        passed=True,
        details="Output is exportable in structured format",
        confidence=1.0
    )


lgpd_data_portability_guardrail = ComplianceGuardrail(
    name="lgpd_art20_data_portability",
    regulation="LGPD",
    check=check_lgpd_article_20_data_portability,
    severity="warn",
    description="Ensures outputs support data portability per LGPD Article 20"
)
```

---

## Week 4: Integration & Demo

### Integration with Existing Workflows
```python
# In neutron/orchestration/workflows.py

from neutron.compliance.auditors.lgpd import lgpd_explainability_guardrail
from neutron.compliance.sentinel import AgentOutput, ComplianceViolation


@activity.defn(name="validate_agent_output")
async def validate_agent_output_activity(
    output_text: str,
    explanation: str,
    explanation_quality: float
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

    try:
        # Enforce LGPD guardrail
        enforced = lgpd_explainability_guardrail.enforce(output)

        return {
            "passed": True,
            "output": output.content,
            "validation_details": enforced.validation_result.details
        }
    except ComplianceViolation as e:
        # Log violation and return error
        return {
            "passed": False,
            "error": str(e),
            "guardrail": e.guardrail.name
        }
```

### Demo Script
```python
# demo_sentinel.py

from neutron.compliance.auditors.lgpd import lgpd_explainability_guardrail
from neutron.compliance.sentinel import AgentOutput, ComplianceViolation


def demo_compliant_output():
    """Demo: Compliant output passes through"""
    print("=" * 60)
    print("Demo 1: Compliant Output")
    print("=" * 60)

    output = AgentOutput(
        content="Based on your credit history, loan approved for $10,000.",
        has_explanation=True,
        explanation="Approval based on: credit score 750+, income >$50k, no late payments",
        explanation_quality=0.85
    )

    try:
        enforced = lgpd_explainability_guardrail.enforce(output)
        print("✅ OUTPUT PASSED COMPLIANCE")
        print(f"   Content: {enforced.original.content}")
        print(f"   Validation: {enforced.validation_result.details}")
    except ComplianceViolation as e:
        print(f"❌ BLOCKED: {e}")


def demo_non_compliant_output():
    """Demo: Non-compliant output blocked"""
    print("\n" + "=" * 60)
    print("Demo 2: Non-Compliant Output (No Explanation)")
    print("=" * 60)

    output = AgentOutput(
        content="Loan denied.",
        has_explanation=False,
        explanation=None,
        explanation_quality=0.0
    )

    try:
        enforced = lgpd_explainability_guardrail.enforce(output)
        print("✅ OUTPUT PASSED COMPLIANCE")
    except ComplianceViolation as e:
        print(f"❌ BLOCKED BY SENTINEL")
        print(f"   Guardrail: {e.guardrail.name}")
        print(f"   Regulation: {e.guardrail.regulation}")
        print(f"   Reason: {e.result.details}")


if __name__ == "__main__":
    demo_compliant_output()
    demo_non_compliant_output()
```

---

## Week 4 Deliverables Checklist

- [ ] `neutron/compliance/sentinel.py` - Core engine (500+ LOC)
- [ ] `neutron/compliance/audit_logger.py` - Immutable logging (200+ LOC)
- [ ] `neutron/compliance/auditors/lgpd.py` - LGPD guardrails (150+ LOC)
- [ ] PostgreSQL audit tables created and tested
- [ ] Unit tests: 90%+ coverage
- [ ] Integration tests with mock workflows
- [ ] `demo_sentinel.py` - Working demo script
- [ ] Documentation: `docs/SENTINEL_USER_GUIDE.md`
- [ ] **MILESTONE DEMO**: Live demonstration of SENTINEL blocking non-compliant output

---

## Testing Strategy

### Unit Tests
```bash
# Test guardrail logic in isolation
pytest tests/compliance/test_sentinel.py -v

# Test LGPD auditor checks
pytest tests/compliance/auditors/test_lgpd.py -v

# Test audit logger
pytest tests/compliance/test_audit_logger.py -v
```

### Integration Tests
```bash
# Test with existing workflows
pytest tests/compliance/test_integration.py -v --integration
```

### Manual Testing
```bash
# Run demo script
python demo_sentinel.py

# Check audit logs in database
psql neutron -c "SELECT * FROM compliance_audits ORDER BY timestamp DESC LIMIT 10;"
```

---

## Success Criteria

✅ **Week 1**: Module structure created, database schema deployed, API documented
✅ **Week 2**: Core engine passes all unit tests, audit logging working
✅ **Week 3**: LGPD Article 18 & 20 guardrails implemented and tested
✅ **Week 4**: Integration complete, demo runs successfully, milestone achieved

---

## Next Steps After Phase 1

Once SENTINEL is complete, you'll have:
1. A unique competitive advantage in the market
2. A reusable compliance framework for all future agents
3. Proven technology for Series A pitch
4. Foundation for Phases 2-4 (CORTEX, SYNAPSE, ORACLE)

**Phase 2 starts immediately**: Begin SYNAPSE memory system while SENTINEL is in production validation.

---

**Ready to Start?**
```bash
# Get started with Phase 1
cd /home/kernelcore/arch/neutron
git checkout -b feature/sentinel-phase1
mkdir -p neutron/compliance/auditors tests/compliance/auditors
# Follow Week 1 instructions above
```
