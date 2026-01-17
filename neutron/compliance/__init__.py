"""
SENTINEL - Compliance Guardrails as Code

The first pillar of NEXUS: Declarative compliance guardrails that are
ENFORCED at runtime, not suggested.

Features:
- Immutable audit trails for every enforcement
- Multi-regulation support (LGPD, GDPR, AI Act, SOC2)
- Declarative policy definitions
- Block/Warn/Audit severity levels
- Integration with Temporal workflows

Example:
    >>> from neutron.compliance import ComplianceGuardrail, AgentOutput
    >>> from neutron.compliance.auditors.lgpd import lgpd_explainability_guardrail
    >>>
    >>> output = AgentOutput(
    ...     content="Loan approved",
    ...     has_explanation=True,
    ...     explanation="Credit score > 750",
    ...     explanation_quality=0.85
    ... )
    >>>
    >>> enforced = lgpd_explainability_guardrail.enforce(output)
    >>> print(enforced.validation_result.passed)  # True
"""

from neutron.compliance.sentinel import (
    ComplianceGuardrail,
    AgentOutput,
    ValidationResult,
    EnforcedOutput,
    ComplianceViolation,
)

from neutron.compliance.audit_logger import AuditLogger

__all__ = [
    "ComplianceGuardrail",
    "AgentOutput",
    "ValidationResult",
    "EnforcedOutput",
    "ComplianceViolation",
    "AuditLogger",
]

__version__ = "0.1.0"
