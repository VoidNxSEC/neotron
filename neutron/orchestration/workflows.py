"""
Temporal Workflow Activities for Compliance Validation

Activities that integrate SENTINEL compliance guardrails with the
Temporal workflow engine for production-ready compliance enforcement.
"""

from typing import Any

from neutron.compliance.sentinel import (
    AgentOutput,
    ComplianceViolation,
)
from neutron.compliance.auditors.lgpd import LGPD_GUARDRAILS


async def validate_agent_output_activity(
    output_text: str,
    explanation: str | None = None,
    explanation_quality: float = 0.0,
    metadata: dict[str, Any] | None = None,
    model_name: str | None = None,
    guardrails: list[str] | None = None,
) -> dict[str, Any]:
    """
    Validate a single agent output against compliance guardrails.

    Args:
        output_text: The agent's output text
        explanation: Explanation of the decision
        explanation_quality: Quality score of the explanation (0.0-1.0)
        metadata: Additional metadata
        model_name: Name of the model that generated the output
        guardrails: Optional list of guardrail names to enforce (default: all LGPD)

    Returns:
        Dict with: passed, output, blocked_by, audit_ids, violations
    """
    # Build AgentOutput
    has_explanation = explanation is not None and len(explanation.strip()) > 0
    output = AgentOutput(
        content=output_text,
        metadata=metadata,
        has_explanation=has_explanation,
        explanation=explanation,
        explanation_quality=explanation_quality if has_explanation else 0.0,
        model_name=model_name,
    )

    # Select guardrails
    active_guardrails = LGPD_GUARDRAILS
    if guardrails:
        active_guardrails = [g for g in LGPD_GUARDRAILS if g.name in guardrails]

    audit_ids = []
    violations = []
    blocked_by = None

    for guardrail in active_guardrails:
        try:
            enforced = guardrail.enforce(output)
            if enforced.audit_id is not None:
                audit_ids.append(enforced.audit_id)

            if not enforced.validation_result.passed:
                violations.append(
                    {
                        "guardrail": guardrail.name,
                        "severity": guardrail.severity,
                        "details": enforced.validation_result.details,
                        "blocked": False,
                    }
                )
        except ComplianceViolation as e:
            blocked_by = guardrail.name
            violations.append(
                {
                    "guardrail": guardrail.name,
                    "severity": guardrail.severity,
                    "details": f"Compliance violation: {e.result.details}",
                    "blocked": True,
                }
            )
            break  # Stop at first blocking violation

    passed = blocked_by is None

    return {
        "passed": passed,
        "output": output_text if passed else None,
        "blocked_by": blocked_by,
        "audit_ids": audit_ids,
        "violations": violations,
    }


async def batch_validate_outputs_activity(
    outputs: list[dict[str, Any]],
    guardrails: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Validate a batch of agent outputs against compliance guardrails.

    Args:
        outputs: List of output dicts with keys: output_text, explanation,
                 explanation_quality, metadata, model_name
        guardrails: Optional list of guardrail names to enforce

    Returns:
        List of validation results (one per output)
    """
    results = []
    for output_dict in outputs:
        result = await validate_agent_output_activity(
            output_text=output_dict.get("output_text", ""),
            explanation=output_dict.get("explanation"),
            explanation_quality=output_dict.get("explanation_quality", 0.0),
            metadata=output_dict.get("metadata"),
            model_name=output_dict.get("model_name"),
            guardrails=guardrails,
        )
        results.append(result)

    return results
