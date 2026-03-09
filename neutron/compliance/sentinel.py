"""
SENTINEL - Core Compliance Guardrail Engine

Declarative compliance guardrails inspired by Open Policy Agent (OPA)
but designed specifically for AI/ML agent outputs.

Philosophy:
    Compliance is not optional. Guardrails are ENFORCED, not suggested.
    Every decision is logged to an immutable audit trail.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

# =============================================================================
# Data Models
# =============================================================================


@dataclass
class ValidationResult:
    """
    Result of a compliance check

    Attributes:
        passed: Whether the validation passed
        details: Human-readable explanation of the result
        confidence: Confidence score (0.0-1.0)
        metadata: Additional context data
    """

    passed: bool
    details: str
    confidence: float = 1.0
    metadata: dict | None = None


@dataclass
class AgentOutput:
    """
    Agent output to be validated against guardrails

    Attributes:
        content: The main output text/data
        metadata: Additional metadata about the output
        has_explanation: Whether an explanation is provided
        explanation: Human-readable explanation (for LGPD Art. 18)
        explanation_quality: Quality score of explanation (0.0-1.0)
        model_name: Name of the model that generated this output
        timestamp: When the output was generated
    """

    content: str
    metadata: dict | None = None
    has_explanation: bool = False
    explanation: str | None = None
    explanation_quality: float = 0.0
    model_name: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EnforcedOutput:
    """
    Wrapped output after compliance enforcement

    Attributes:
        original: The original agent output
        validation_result: Result of the compliance check
        guardrail_name: Name of the guardrail that was applied
        regulation: Regulation this guardrail enforces
        enforced: Whether enforcement was applied
        audit_id: ID of the audit log entry
    """

    original: AgentOutput
    validation_result: ValidationResult
    guardrail_name: str
    regulation: str
    enforced: bool
    audit_id: int | None = None


# =============================================================================
# Exceptions
# =============================================================================


class ComplianceViolation(Exception):  # noqa: N818
    """
    Raised when a blocking guardrail fails

    This exception contains full context about the violation for
    debugging and audit purposes.
    """

    def __init__(
        self, guardrail: "ComplianceGuardrail", result: ValidationResult, output: AgentOutput
    ):
        self.guardrail = guardrail
        self.result = result
        self.output = output

        message = (
            f"Compliance violation: {guardrail.name} "
            f"({guardrail.regulation})\n"
            f"Severity: {guardrail.severity}\n"
            f"Details: {result.details}\n"
            f"Confidence: {result.confidence:.2f}"
        )

        super().__init__(message)


# =============================================================================
# Core Guardrail Class
# =============================================================================


@dataclass
class ComplianceGuardrail:
    """
    Declarative compliance guardrail

    Guardrails are declarative policies that are ENFORCED at runtime.
    Each guardrail is tied to a specific regulation (LGPD, GDPR, etc.)
    and logs to an immutable audit trail.

    Attributes:
        name: Unique identifier for this guardrail
        regulation: Which regulation this enforces (LGPD, GDPR, AI_ACT, SOC2)
        check: Validation function (AgentOutput -> ValidationResult)
        severity: Enforcement level (block, warn, audit)
        description: Human-readable description of what this checks
        enabled: Whether this guardrail is currently active

    Example:
        >>> def check_explanation(output: AgentOutput) -> ValidationResult:
        ...     if not output.has_explanation:
        ...         return ValidationResult(False, "No explanation provided")
        ...     return ValidationResult(True, "Explanation provided")
        ...
        >>> guardrail = ComplianceGuardrail(
        ...     name="lgpd_art18_explanation",
        ...     regulation="LGPD",
        ...     check=check_explanation,
        ...     severity="block"
        ... )
        ...
        >>> output = AgentOutput(content="Result", has_explanation=False)
        >>> try:
        ...     enforced = guardrail.enforce(output)
        ... except ComplianceViolation as e:
        ...     print(f"Blocked: {e}")
    """

    name: str
    regulation: Literal["LGPD", "GDPR", "AI_ACT", "SOC2"]
    check: Callable[[AgentOutput], ValidationResult]
    severity: Literal["block", "warn", "audit"]
    description: str = ""
    enabled: bool = True

    def __post_init__(self):
        """Initialize audit logger after dataclass initialization"""
        from neutron.compliance.audit_logger import AuditLogger

        self._audit_logger = AuditLogger()

    def enforce(self, output: AgentOutput) -> EnforcedOutput:
        """
        Enforce guardrail on agent output

        This method:
        1. Runs the compliance check
        2. Logs the result to immutable audit trail
        3. Enforces based on severity (block/warn/audit)
        4. Returns wrapped output with validation results

        Args:
            output: Agent output to validate

        Returns:
            EnforcedOutput with validation results

        Raises:
            ComplianceViolation: If severity="block" and validation fails
        """

        if not self.enabled:
            # If guardrail is disabled, pass through without validation
            return EnforcedOutput(
                original=output,
                validation_result=ValidationResult(
                    passed=True, details=f"Guardrail {self.name} is disabled"
                ),
                guardrail_name=self.name,
                regulation=self.regulation,
                enforced=False,
            )

        # Run compliance check
        result = self.check(output)

        # Compute hash of output for audit trail
        output_hash = self._hash_output(output)

        # Log to immutable audit store
        audit_id = self._audit_logger.log(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrail_name": self.name,
                "regulation": self.regulation,
                "agent_output_hash": output_hash,
                "validation_result": {
                    "passed": result.passed,
                    "details": result.details,
                    "confidence": result.confidence,
                    "metadata": result.metadata,
                },
                "severity": self.severity,
                "passed": result.passed,
                "model_name": output.model_name,
            }
        )

        # Enforce based on severity
        if not result.passed and self.severity == "block":
            raise ComplianceViolation(self, result, output)

        return EnforcedOutput(
            original=output,
            validation_result=result,
            guardrail_name=self.name,
            regulation=self.regulation,
            enforced=True,
            audit_id=audit_id,
        )

    def _hash_output(self, output: AgentOutput) -> str:
        """
        Generate SHA-256 hash of output for audit trail

        This creates a cryptographic hash of the output content and metadata
        for tamper-proof audit logging.
        """
        content = json.dumps(
            {
                "content": output.content,
                "metadata": output.metadata,
                "timestamp": output.timestamp.isoformat(),
            },
            sort_keys=True,
        )

        return hashlib.sha256(content.encode()).hexdigest()

    def disable(self):
        """Disable this guardrail"""
        self.enabled = False

    def enable(self):
        """Enable this guardrail"""
        self.enabled = True


# =============================================================================
# Utility Functions
# =============================================================================


def create_guardrail(
    name: str,
    regulation: Literal["LGPD", "GDPR", "AI_ACT", "SOC2"],
    check_function: Callable[[AgentOutput], ValidationResult],
    severity: Literal["block", "warn", "audit"] = "block",
    description: str = "",
) -> ComplianceGuardrail:
    """
    Convenience function to create a guardrail

    Args:
        name: Unique identifier
        regulation: Which regulation this enforces
        check_function: Validation function
        severity: Enforcement level
        description: Human-readable description

    Returns:
        ComplianceGuardrail instance
    """
    return ComplianceGuardrail(
        name=name,
        regulation=regulation,
        check=check_function,
        severity=severity,
        description=description,
    )
