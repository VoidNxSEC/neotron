"""
LGPD Compliance Auditors

Lei Geral de Proteção de Dados (Brazil's General Data Protection Law)

This module implements LGPD-specific compliance guardrails for AI agent outputs.

Key LGPD Articles Implemented:
- Article 18: Right to review automated decisions (requires explanation)
- Article 20: Right to data portability (requires exportable format)

Reference: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
"""

from neutron.compliance.sentinel import (
    ComplianceGuardrail,
    AgentOutput,
    ValidationResult,
    create_guardrail
)
from typing import List


# =============================================================================
# LGPD Article 18 - Right to Explanation
# =============================================================================

def check_lgpd_article_18_explanation(output: AgentOutput) -> ValidationResult:
    """
    LGPD Article 18: Right to review automated decisions

    Article 18 guarantees the right to:
    "...obtain clear and adequate information about the criteria and
    procedures used for an automated decision."

    Requirements:
    - Explanation must be present
    - Explanation quality must be adequate (>= 0.7)
    - Explanation must not be empty

    Args:
        output: Agent output to validate

    Returns:
        ValidationResult indicating compliance status
    """

    # Check 1: Explanation presence
    if not output.has_explanation:
        return ValidationResult(
            passed=False,
            details=(
                "LGPD Article 18 violation: No explanation provided for automated decision. "
                "Automated decisions affecting data subjects must include clear explanations "
                "of the criteria and procedures used."
            ),
            confidence=1.0,
            metadata={
                "article": "LGPD Article 18",
                "requirement": "explanation_presence",
                "violation_type": "missing_explanation"
            }
        )

    # Check 2: Explanation not empty
    if not output.explanation or len(output.explanation.strip()) == 0:
        return ValidationResult(
            passed=False,
            details=(
                "LGPD Article 18 violation: Explanation is empty. "
                "Explanation must contain substantive information about the decision criteria."
            ),
            confidence=1.0,
            metadata={
                "article": "LGPD Article 18",
                "requirement": "explanation_content",
                "violation_type": "empty_explanation"
            }
        )

    # Check 3: Explanation quality threshold
    quality_threshold = 0.7
    if output.explanation_quality < quality_threshold:
        return ValidationResult(
            passed=False,
            details=(
                f"LGPD Article 18 violation: Explanation quality insufficient. "
                f"Quality score: {output.explanation_quality:.2f} (minimum: {quality_threshold:.2f}). "
                f"Explanations must be clear, adequate, and comprehensible to data subjects."
            ),
            confidence=output.explanation_quality,
            metadata={
                "article": "LGPD Article 18",
                "requirement": "explanation_quality",
                "violation_type": "low_quality_explanation",
                "quality_score": output.explanation_quality,
                "threshold": quality_threshold
            }
        )

    # Check 4: Minimum explanation length (basic heuristic)
    min_length = 20
    if len(output.explanation) < min_length:
        return ValidationResult(
            passed=False,
            details=(
                f"LGPD Article 18 violation: Explanation too short ({len(output.explanation)} characters). "
                f"Explanations must be substantive (minimum {min_length} characters)."
            ),
            confidence=0.8,
            metadata={
                "article": "LGPD Article 18",
                "requirement": "explanation_length",
                "violation_type": "insufficient_explanation",
                "length": len(output.explanation),
                "min_length": min_length
            }
        )

    # All checks passed
    return ValidationResult(
        passed=True,
        details=(
            f"LGPD Article 18 compliant: Adequate explanation provided. "
            f"Quality: {output.explanation_quality:.2f}, Length: {len(output.explanation)} chars."
        ),
        confidence=1.0,
        metadata={
            "article": "LGPD Article 18",
            "quality_score": output.explanation_quality,
            "explanation_length": len(output.explanation)
        }
    )


# =============================================================================
# LGPD Article 20 - Data Portability
# =============================================================================

def check_lgpd_article_20_portability(output: AgentOutput) -> ValidationResult:
    """
    LGPD Article 20: Right to data portability

    Article 20 guarantees the right to:
    "...request the portability of personal data to another service or
    product provider, through an express request."

    For AI agent outputs, this means the output must be in a format
    that can be easily exported and transferred.

    Requirements:
    - Output must have exportable format specified
    - Format must be machine-readable (JSON, CSV, XML, etc.)
    - Data structure must be documented

    Args:
        output: Agent output to validate

    Returns:
        ValidationResult indicating compliance status
    """

    # Check 1: Metadata presence
    if not output.metadata:
        return ValidationResult(
            passed=False,
            details=(
                "LGPD Article 20 violation: No metadata provided. "
                "Outputs must include metadata specifying exportable format for data portability."
            ),
            confidence=1.0,
            metadata={
                "article": "LGPD Article 20",
                "requirement": "metadata_presence",
                "violation_type": "missing_metadata"
            }
        )

    # Check 2: Exportable format specified
    exportable_format = output.metadata.get("exportable_format")
    if not exportable_format:
        return ValidationResult(
            passed=False,
            details=(
                "LGPD Article 20 violation: No exportable format specified. "
                "Metadata must include 'exportable_format' field (e.g., 'json', 'csv', 'xml')."
            ),
            confidence=1.0,
            metadata={
                "article": "LGPD Article 20",
                "requirement": "format_specification",
                "violation_type": "missing_format"
            }
        )

    # Check 3: Format is machine-readable
    machine_readable_formats = {
        "json", "csv", "xml", "parquet", "avro",
        "yaml", "toml", "jsonl", "tsv"
    }

    format_lower = str(exportable_format).lower()
    if format_lower not in machine_readable_formats:
        return ValidationResult(
            passed=False,
            details=(
                f"LGPD Article 20 violation: Format '{exportable_format}' is not machine-readable. "
                f"Valid formats: {', '.join(sorted(machine_readable_formats))}."
            ),
            confidence=0.9,
            metadata={
                "article": "LGPD Article 20",
                "requirement": "machine_readable_format",
                "violation_type": "invalid_format",
                "provided_format": exportable_format,
                "valid_formats": list(machine_readable_formats)
            }
        )

    # Check 4: Data structure documented
    data_structure = output.metadata.get("data_structure")
    if not data_structure:
        return ValidationResult(
            passed=False,
            details=(
                "LGPD Article 20 violation: Data structure not documented. "
                "Metadata must include 'data_structure' describing the schema for portability."
            ),
            confidence=0.8,
            metadata={
                "article": "LGPD Article 20",
                "requirement": "structure_documentation",
                "violation_type": "missing_schema"
            }
        )

    # All checks passed
    return ValidationResult(
        passed=True,
        details=(
            f"LGPD Article 20 compliant: Data is portable. "
            f"Format: {exportable_format}, Structure documented."
        ),
        confidence=1.0,
        metadata={
            "article": "LGPD Article 20",
            "exportable_format": exportable_format,
            "data_structure": data_structure
        }
    )


# =============================================================================
# Pre-configured LGPD Guardrails
# =============================================================================

# LGPD Article 18 - Right to Explanation (BLOCKING)
lgpd_art18_explanation_guardrail = ComplianceGuardrail(
    name="lgpd_art18_explanation",
    regulation="LGPD",
    check=check_lgpd_article_18_explanation,
    severity="block",
    description=(
        "LGPD Article 18 - Right to Explanation. "
        "Ensures automated decisions include clear, adequate explanations "
        "of the criteria and procedures used. This is a BLOCKING guardrail - "
        "outputs without proper explanations will be rejected."
    )
)

# LGPD Article 20 - Data Portability (WARNING)
lgpd_art20_portability_guardrail = ComplianceGuardrail(
    name="lgpd_art20_portability",
    regulation="LGPD",
    check=check_lgpd_article_20_portability,
    severity="warn",
    description=(
        "LGPD Article 20 - Data Portability. "
        "Ensures outputs are in machine-readable formats that can be exported "
        "and transferred. This is a WARNING guardrail - violations are logged "
        "but do not block output."
    )
)

# Combined LGPD guardrail suite
LGPD_GUARDRAILS: List[ComplianceGuardrail] = [
    lgpd_art18_explanation_guardrail,
    lgpd_art20_portability_guardrail
]


# =============================================================================
# Convenience Functions
# =============================================================================

def get_lgpd_guardrails() -> List[ComplianceGuardrail]:
    """
    Get all LGPD compliance guardrails

    Returns:
        List of pre-configured LGPD guardrails
    """
    return LGPD_GUARDRAILS.copy()


def get_lgpd_guardrail_by_article(article_number: int) -> ComplianceGuardrail:
    """
    Get LGPD guardrail by article number

    Args:
        article_number: LGPD article number (18 or 20)

    Returns:
        ComplianceGuardrail for the specified article

    Raises:
        ValueError: If article number is not implemented
    """
    guardrail_map = {
        18: lgpd_art18_explanation_guardrail,
        20: lgpd_art20_portability_guardrail
    }

    if article_number not in guardrail_map:
        raise ValueError(
            f"LGPD Article {article_number} not implemented. "
            f"Available articles: {list(guardrail_map.keys())}"
        )

    return guardrail_map[article_number]


def validate_with_lgpd(output: AgentOutput) -> List[ValidationResult]:
    """
    Validate output against all LGPD guardrails

    This is a convenience function that runs all LGPD guardrails
    and returns the results without enforcing (for batch validation).

    Args:
        output: Agent output to validate

    Returns:
        List of ValidationResult for each guardrail
    """
    results = []
    for guardrail in LGPD_GUARDRAILS:
        result = guardrail.check(output)
        results.append(result)
    return results
