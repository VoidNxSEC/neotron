"""
GDPR Compliance Auditors

General Data Protection Regulation (EU)

This module implements GDPR-specific compliance guardrails for AI agent outputs.

Key GDPR Articles Implemented:
- Article 15: Right to Access (data export)
- Article 17: Right to Erasure (delete data)
- Article 22: Right not to be subject to automated decision-making (human oversight)

Reference: https://gdpr-info.eu/
"""

from neutron.compliance.sentinel import (
    ComplianceGuardrail,
    AgentOutput,
    ValidationResult,
    create_guardrail
)
from typing import List, Dict, Any, Optional
from datetime import datetime


# =============================================================================
# GDPR Article 22 - Automated Decision-Making & Human Oversight
# =============================================================================

def check_gdpr_article_22_human_oversight(output: AgentOutput) -> ValidationResult:
    """
    GDPR Article 22: Right not to be subject to automated decision-making

    Article 22 states:
    "The data subject shall have the right not to be subject to a decision
    based solely on automated processing, including profiling, which produces
    legal effects concerning him or her or similarly significantly affects him or her."

    For high-risk automated decisions, human oversight is required.

    Requirements:
    - High-risk decisions must have human_reviewed flag
    - Must include human reviewer ID
    - Review timestamp must be present
    - Human can override automated decision

    Args:
        output: Agent output to validate

    Returns:
        ValidationResult indicating compliance status
    """

    # Check if decision is high-risk
    if not output.metadata:
        return ValidationResult(
            passed=False,
            details=(
                "GDPR Article 22 violation: No metadata provided. "
                "Cannot determine risk level for automated decision."
            ),
            confidence=1.0,
            metadata={
                "article": "GDPR Article 22",
                "requirement": "metadata_presence",
                "violation_type": "missing_metadata"
            }
        )

    risk_level = output.metadata.get("risk_level", "unknown")

    # Low-risk decisions don't require human oversight
    if risk_level == "low":
        return ValidationResult(
            passed=True,
            details="GDPR Article 22 compliant: Low-risk automated decision",
            confidence=1.0,
            metadata={"article": "GDPR Article 22", "risk_level": "low"}
        )

    # High/medium risk decisions require human oversight
    if risk_level in ["high", "medium"]:
        human_reviewed = output.metadata.get("human_reviewed", False)
        reviewer_id = output.metadata.get("reviewer_id")
        review_timestamp = output.metadata.get("review_timestamp")

        # Check human review flag
        if not human_reviewed:
            return ValidationResult(
                passed=False,
                details=(
                    f"GDPR Article 22 violation: {risk_level.capitalize()}-risk automated decision "
                    f"requires human oversight before delivery. "
                    f"Set metadata['human_reviewed'] = True after review."
                ),
                confidence=1.0,
                metadata={
                    "article": "GDPR Article 22",
                    "requirement": "human_oversight",
                    "violation_type": "missing_human_review",
                    "risk_level": risk_level
                }
            )

        # Check reviewer ID
        if not reviewer_id:
            return ValidationResult(
                passed=False,
                details=(
                    "GDPR Article 22 violation: Human reviewer ID required. "
                    "Set metadata['reviewer_id'] to identify who reviewed the decision."
                ),
                confidence=0.9,
                metadata={
                    "article": "GDPR Article 22",
                    "requirement": "reviewer_identification",
                    "violation_type": "missing_reviewer_id"
                }
            )

        # Check review timestamp
        if not review_timestamp:
            return ValidationResult(
                passed=False,
                details=(
                    "GDPR Article 22 violation: Review timestamp required. "
                    "Set metadata['review_timestamp'] to document when review occurred."
                ),
                confidence=0.9,
                metadata={
                    "article": "GDPR Article 22",
                    "requirement": "review_timestamp",
                    "violation_type": "missing_review_timestamp"
                }
            )

        # All checks passed
        return ValidationResult(
            passed=True,
            details=(
                f"GDPR Article 22 compliant: {risk_level.capitalize()}-risk decision "
                f"reviewed by {reviewer_id} at {review_timestamp}"
            ),
            confidence=1.0,
            metadata={
                "article": "GDPR Article 22",
                "risk_level": risk_level,
                "reviewer_id": reviewer_id,
                "review_timestamp": review_timestamp
            }
        )

    # Unknown risk level - fail safe
    return ValidationResult(
        passed=False,
        details=(
            f"GDPR Article 22 violation: Unknown risk level '{risk_level}'. "
            f"Must be 'low', 'medium', or 'high'."
        ),
        confidence=1.0,
        metadata={
            "article": "GDPR Article 22",
            "violation_type": "invalid_risk_level",
            "provided_risk_level": risk_level
        }
    )


# =============================================================================
# GDPR Article 15 - Right to Access
# =============================================================================

def check_gdpr_article_15_data_access(output: AgentOutput) -> ValidationResult:
    """
    GDPR Article 15: Right of Access by the Data Subject

    Article 15 grants individuals the right to access their personal data.
    When AI agents process personal data, the output must be accessible
    to the data subject upon request.

    Requirements:
    - Output must include data_access_enabled flag
    - Must specify data categories processed
    - Must include retention period
    - Must provide export format

    Args:
        output: Agent output to validate

    Returns:
        ValidationResult indicating compliance status
    """

    if not output.metadata:
        return ValidationResult(
            passed=False,
            details=(
                "GDPR Article 15 violation: No metadata provided. "
                "Cannot verify data access compliance."
            ),
            confidence=1.0,
            metadata={
                "article": "GDPR Article 15",
                "requirement": "metadata_presence",
                "violation_type": "missing_metadata"
            }
        )

    # Check data access enabled
    data_access_enabled = output.metadata.get("data_access_enabled", False)
    if not data_access_enabled:
        return ValidationResult(
            passed=False,
            details=(
                "GDPR Article 15 violation: Data access must be enabled. "
                "Set metadata['data_access_enabled'] = True to allow data subject access."
            ),
            confidence=1.0,
            metadata={
                "article": "GDPR Article 15",
                "requirement": "data_access",
                "violation_type": "access_disabled"
            }
        )

    # Check data categories
    data_categories = output.metadata.get("data_categories")
    if not data_categories:
        return ValidationResult(
            passed=False,
            details=(
                "GDPR Article 15 violation: Data categories must be specified. "
                "Set metadata['data_categories'] to list what personal data was processed."
            ),
            confidence=0.9,
            metadata={
                "article": "GDPR Article 15",
                "requirement": "data_categories",
                "violation_type": "missing_categories"
            }
        )

    # Check retention period
    retention_period = output.metadata.get("retention_period")
    if not retention_period:
        return ValidationResult(
            passed=False,
            details=(
                "GDPR Article 15 violation: Data retention period must be specified. "
                "Set metadata['retention_period'] to inform how long data is kept."
            ),
            confidence=0.8,
            metadata={
                "article": "GDPR Article 15",
                "requirement": "retention_period",
                "violation_type": "missing_retention"
            }
        )

    # Check export format
    export_format = output.metadata.get("export_format")
    if not export_format:
        return ValidationResult(
            passed=False,
            details=(
                "GDPR Article 15 violation: Export format must be specified. "
                "Set metadata['export_format'] for data portability."
            ),
            confidence=0.8,
            metadata={
                "article": "GDPR Article 15",
                "requirement": "export_format",
                "violation_type": "missing_export_format"
            }
        )

    # All checks passed
    return ValidationResult(
        passed=True,
        details=(
            f"GDPR Article 15 compliant: Data access enabled. "
            f"Categories: {data_categories}, "
            f"Retention: {retention_period}, "
            f"Export: {export_format}"
        ),
        confidence=1.0,
        metadata={
            "article": "GDPR Article 15",
            "data_categories": data_categories,
            "retention_period": retention_period,
            "export_format": export_format
        }
    )


# =============================================================================
# GDPR Article 17 - Right to Erasure (Handled by MemoryStore)
# =============================================================================

def check_gdpr_article_17_erasure_support(output: AgentOutput) -> ValidationResult:
    """
    GDPR Article 17: Right to Erasure ("Right to be Forgotten")

    Article 17 grants individuals the right to request deletion of their personal data.

    This check verifies that the system SUPPORTS erasure (not that it was performed).
    Actual erasure is handled by MemoryStore.delete_by_customer().

    Requirements:
    - Output must indicate erasure support
    - Must provide erasure endpoint/method
    - Must document erasure process

    Args:
        output: Agent output to validate

    Returns:
        ValidationResult indicating compliance status
    """

    if not output.metadata:
        # Erasure support is optional for some outputs
        return ValidationResult(
            passed=True,
            details=(
                "GDPR Article 17: Erasure support not applicable (no personal data)"
            ),
            confidence=1.0,
            metadata={"article": "GDPR Article 17"}
        )

    # Check if personal data is involved
    processes_personal_data = output.metadata.get("processes_personal_data", False)

    if not processes_personal_data:
        # No personal data = no erasure requirement
        return ValidationResult(
            passed=True,
            details="GDPR Article 17: No personal data processed, erasure not required",
            confidence=1.0,
            metadata={"article": "GDPR Article 17"}
        )

    # Personal data is processed - check erasure support
    erasure_supported = output.metadata.get("erasure_supported", False)
    if not erasure_supported:
        return ValidationResult(
            passed=False,
            details=(
                "GDPR Article 17 violation: Erasure must be supported for personal data. "
                "Set metadata['erasure_supported'] = True"
            ),
            confidence=1.0,
            metadata={
                "article": "GDPR Article 17",
                "requirement": "erasure_support",
                "violation_type": "erasure_not_supported"
            }
        )

    # Check erasure endpoint
    erasure_endpoint = output.metadata.get("erasure_endpoint")
    if not erasure_endpoint:
        return ValidationResult(
            passed=False,
            details=(
                "GDPR Article 17 violation: Erasure endpoint must be documented. "
                "Set metadata['erasure_endpoint'] to API/method for deletion requests."
            ),
            confidence=0.9,
            metadata={
                "article": "GDPR Article 17",
                "requirement": "erasure_endpoint",
                "violation_type": "missing_endpoint"
            }
        )

    # All checks passed
    return ValidationResult(
        passed=True,
        details=(
            f"GDPR Article 17 compliant: Erasure supported via {erasure_endpoint}"
        ),
        confidence=1.0,
        metadata={
            "article": "GDPR Article 17",
            "erasure_endpoint": erasure_endpoint
        }
    )


# =============================================================================
# Pre-configured GDPR Guardrails
# =============================================================================

# GDPR Article 22 - Human Oversight (BLOCKING)
gdpr_art22_human_oversight_guardrail = ComplianceGuardrail(
    name="gdpr_art22_human_oversight",
    regulation="GDPR",
    check=check_gdpr_article_22_human_oversight,
    severity="block",
    description=(
        "GDPR Article 22 - Automated Decision-Making. "
        "Ensures high-risk automated decisions have human oversight. "
        "This is a BLOCKING guardrail - high-risk decisions without "
        "human review will be rejected."
    )
)

# GDPR Article 15 - Right to Access (WARNING)
gdpr_art15_data_access_guardrail = ComplianceGuardrail(
    name="gdpr_art15_data_access",
    regulation="GDPR",
    check=check_gdpr_article_15_data_access,
    severity="warn",
    description=(
        "GDPR Article 15 - Right to Access. "
        "Ensures data subjects can access their personal data. "
        "This is a WARNING guardrail - violations are logged "
        "but do not block output."
    )
)

# GDPR Article 17 - Right to Erasure (WARNING)
gdpr_art17_erasure_support_guardrail = ComplianceGuardrail(
    name="gdpr_art17_erasure_support",
    regulation="GDPR",
    check=check_gdpr_article_17_erasure_support,
    severity="warn",
    description=(
        "GDPR Article 17 - Right to Erasure. "
        "Ensures erasure is supported for personal data processing. "
        "This is a WARNING guardrail - violations are logged "
        "but do not block output."
    )
)

# Combined GDPR guardrail suite
GDPR_GUARDRAILS: List[ComplianceGuardrail] = [
    gdpr_art22_human_oversight_guardrail,
    gdpr_art15_data_access_guardrail,
    gdpr_art17_erasure_support_guardrail,
]


# =============================================================================
# Convenience Functions
# =============================================================================

def get_gdpr_guardrails() -> List[ComplianceGuardrail]:
    """
    Get all GDPR compliance guardrails

    Returns:
        List of pre-configured GDPR guardrails
    """
    return GDPR_GUARDRAILS.copy()


def get_gdpr_guardrail_by_article(article_number: int) -> ComplianceGuardrail:
    """
    Get GDPR guardrail by article number

    Args:
        article_number: GDPR article number (15, 17, or 22)

    Returns:
        ComplianceGuardrail for the specified article

    Raises:
        ValueError: If article number is not implemented
    """
    guardrail_map = {
        15: gdpr_art15_data_access_guardrail,
        17: gdpr_art17_erasure_support_guardrail,
        22: gdpr_art22_human_oversight_guardrail,
    }

    if article_number not in guardrail_map:
        raise ValueError(
            f"GDPR Article {article_number} not implemented. "
            f"Available articles: {list(guardrail_map.keys())}"
        )

    return guardrail_map[article_number]


def validate_with_gdpr(output: AgentOutput) -> List[ValidationResult]:
    """
    Validate output against all GDPR guardrails

    This is a convenience function that runs all GDPR guardrails
    and returns the results without enforcing (for batch validation).

    Args:
        output: Agent output to validate

    Returns:
        List of ValidationResult for each guardrail
    """
    results = []
    for guardrail in GDPR_GUARDRAILS:
        result = guardrail.check(output)
        results.append(result)
    return results


# =============================================================================
# Erasure Handler (Integration with SYNAPSE)
# =============================================================================

class GDPRErasureHandler:
    """
    Handles GDPR Article 17 erasure requests

    Integrates with SYNAPSE MemoryStore to delete customer data.
    """

    def __init__(self, memory_store=None):
        """
        Initialize erasure handler

        Args:
            memory_store: Optional MemoryStore instance
        """
        self.memory_store = memory_store

    def erase_customer_data(self, customer_id: str) -> Dict[str, Any]:
        """
        Erase all data for a customer (GDPR Article 17)

        Args:
            customer_id: Customer ID

        Returns:
            Dict with erasure results
        """
        if not self.memory_store:
            from neutron.memory import MemoryStore
            self.memory_store = MemoryStore()

        # Delete from memory store
        deleted_memories = self.memory_store.delete_by_customer(customer_id)

        # Log erasure to compliance audit
        from neutron.compliance.audit_logger import AuditLogger
        logger = AuditLogger()

        audit_id = logger.log({
            "event": "gdpr_art17_erasure",
            "regulation": "GDPR",
            "customer_id": customer_id,
            "deleted_memories": deleted_memories,
            "timestamp": datetime.utcnow().isoformat(),
            "article": "GDPR Article 17",
            "guardrail_name": "gdpr_art17_erasure_handler",
            "passed": True,
            "severity": "audit"
        })

        return {
            "customer_id": customer_id,
            "deleted_memories": deleted_memories,
            "audit_id": audit_id,
            "status": "completed"
        }
