"""
Tests for LGPD Compliance Auditors

Tests for Lei Geral de Proteção de Dados (Brazil's GDPR) compliance guardrails.
"""

import pytest
from datetime import datetime

from neutron.compliance.sentinel import (
    AgentOutput,
    ValidationResult,
    ComplianceViolation
)
from neutron.compliance.auditors.lgpd import (
    check_lgpd_article_18_explanation,
    check_lgpd_article_20_portability,
    lgpd_art18_explanation_guardrail,
    lgpd_art20_portability_guardrail,
    get_lgpd_guardrails,
    get_lgpd_guardrail_by_article,
    validate_with_lgpd
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def compliant_output_art18():
    """Agent output compliant with LGPD Article 18"""
    return AgentOutput(
        content="Loan approved for $50,000 at 5.2% APR",
        has_explanation=True,
        explanation=(
            "Loan approved based on the following criteria: "
            "credit score of 780 (excellent), annual income of $85,000, "
            "debt-to-income ratio of 22%, no late payments in last 24 months, "
            "and 8 years of credit history."
        ),
        explanation_quality=0.85,
        model_name="risk-assessment-v2"
    )


@pytest.fixture
def non_compliant_output_no_explanation():
    """Agent output missing explanation (Article 18 violation)"""
    return AgentOutput(
        content="Loan denied",
        has_explanation=False,
        explanation=None,
        explanation_quality=0.0,
        model_name="risk-assessment-v2"
    )


@pytest.fixture
def non_compliant_output_low_quality():
    """Agent output with low quality explanation"""
    return AgentOutput(
        content="Loan approved",
        has_explanation=True,
        explanation="Approved.",
        explanation_quality=0.3,
        model_name="risk-assessment-v2"
    )


@pytest.fixture
def compliant_output_art20():
    """Agent output compliant with LGPD Article 20"""
    return AgentOutput(
        content='{"customer_id": "12345", "risk_score": 0.85}',
        metadata={
            "exportable_format": "json",
            "data_structure": {
                "customer_id": "string",
                "risk_score": "float"
            }
        },
        model_name="risk-assessment-v2"
    )


@pytest.fixture
def non_compliant_output_no_format():
    """Agent output without exportable format (Article 20 violation)"""
    return AgentOutput(
        content="Customer risk is high",
        metadata={"some_field": "value"},
        model_name="risk-assessment-v2"
    )


# =============================================================================
# LGPD Article 18 Tests - Right to Explanation
# =============================================================================

class TestLGPDArticle18:
    """Tests for LGPD Article 18 - Right to Explanation"""

    def test_compliant_output_passes(self, compliant_output_art18):
        """Test that compliant output passes Article 18 check"""
        result = check_lgpd_article_18_explanation(compliant_output_art18)

        assert result.passed is True
        assert "compliant" in result.details.lower()
        assert result.confidence == 1.0
        assert result.metadata["article"] == "LGPD Article 18"

    def test_missing_explanation_fails(self, non_compliant_output_no_explanation):
        """Test that missing explanation fails Article 18 check"""
        result = check_lgpd_article_18_explanation(non_compliant_output_no_explanation)

        assert result.passed is False
        assert "violation" in result.details.lower()
        assert "no explanation" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_explanation"

    def test_empty_explanation_fails(self):
        """Test that empty explanation fails Article 18 check"""
        output = AgentOutput(
            content="Decision made",
            has_explanation=True,
            explanation="   ",  # Empty/whitespace only
            explanation_quality=0.8
        )

        result = check_lgpd_article_18_explanation(output)

        assert result.passed is False
        assert "empty" in result.details.lower()
        assert result.metadata["violation_type"] == "empty_explanation"

    def test_low_quality_explanation_fails(self, non_compliant_output_low_quality):
        """Test that low quality explanation fails Article 18 check"""
        result = check_lgpd_article_18_explanation(non_compliant_output_low_quality)

        assert result.passed is False
        assert "quality insufficient" in result.details.lower()
        assert result.metadata["violation_type"] == "low_quality_explanation"
        assert result.metadata["quality_score"] == 0.3
        assert result.metadata["threshold"] == 0.7

    def test_short_explanation_fails(self):
        """Test that too-short explanation fails Article 18 check"""
        output = AgentOutput(
            content="Decision made",
            has_explanation=True,
            explanation="Approved.",  # Too short
            explanation_quality=0.8
        )

        result = check_lgpd_article_18_explanation(output)

        assert result.passed is False
        assert "too short" in result.details.lower()
        assert result.metadata["violation_type"] == "insufficient_explanation"

    def test_quality_threshold_boundary(self):
        """Test explanation quality threshold at boundary (0.7)"""
        # Just below threshold - should fail
        output_below = AgentOutput(
            content="Decision",
            has_explanation=True,
            explanation="This is a sufficient explanation for testing purposes.",
            explanation_quality=0.69
        )
        result_below = check_lgpd_article_18_explanation(output_below)
        assert result_below.passed is False

        # At threshold - should pass
        output_at = AgentOutput(
            content="Decision",
            has_explanation=True,
            explanation="This is a sufficient explanation for testing purposes.",
            explanation_quality=0.7
        )
        result_at = check_lgpd_article_18_explanation(output_at)
        assert result_at.passed is True


# =============================================================================
# LGPD Article 20 Tests - Data Portability
# =============================================================================

class TestLGPDArticle20:
    """Tests for LGPD Article 20 - Data Portability"""

    def test_compliant_output_passes(self, compliant_output_art20):
        """Test that compliant output passes Article 20 check"""
        result = check_lgpd_article_20_portability(compliant_output_art20)

        assert result.passed is True
        assert "compliant" in result.details.lower()
        assert result.metadata["article"] == "LGPD Article 20"
        assert result.metadata["exportable_format"] == "json"

    def test_missing_metadata_fails(self):
        """Test that missing metadata fails Article 20 check"""
        output = AgentOutput(
            content="Some data",
            metadata=None
        )

        result = check_lgpd_article_20_portability(output)

        assert result.passed is False
        assert "no metadata" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_metadata"

    def test_missing_format_fails(self, non_compliant_output_no_format):
        """Test that missing exportable format fails Article 20 check"""
        result = check_lgpd_article_20_portability(non_compliant_output_no_format)

        assert result.passed is False
        assert "no exportable format" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_format"

    def test_invalid_format_fails(self):
        """Test that non-machine-readable format fails Article 20 check"""
        output = AgentOutput(
            content="Some data",
            metadata={
                "exportable_format": "pdf",  # Not machine-readable
                "data_structure": {"field": "type"}
            }
        )

        result = check_lgpd_article_20_portability(output)

        assert result.passed is False
        assert "not machine-readable" in result.details.lower()
        assert result.metadata["violation_type"] == "invalid_format"
        assert result.metadata["provided_format"] == "pdf"

    def test_missing_data_structure_fails(self):
        """Test that missing data structure fails Article 20 check"""
        output = AgentOutput(
            content="Some data",
            metadata={
                "exportable_format": "json"
                # Missing data_structure
            }
        )

        result = check_lgpd_article_20_portability(output)

        assert result.passed is False
        assert "structure not documented" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_schema"

    def test_valid_formats(self):
        """Test that all valid machine-readable formats pass"""
        valid_formats = ["json", "csv", "xml", "parquet", "yaml", "jsonl"]

        for fmt in valid_formats:
            output = AgentOutput(
                content="Data",
                metadata={
                    "exportable_format": fmt,
                    "data_structure": {"field": "type"}
                }
            )
            result = check_lgpd_article_20_portability(output)
            assert result.passed is True, f"Format {fmt} should be valid"

    def test_case_insensitive_format(self):
        """Test that format checking is case-insensitive"""
        output = AgentOutput(
            content="Data",
            metadata={
                "exportable_format": "JSON",  # Uppercase
                "data_structure": {"field": "type"}
            }
        )

        result = check_lgpd_article_20_portability(output)
        assert result.passed is True


# =============================================================================
# Guardrail Enforcement Tests
# =============================================================================

class TestLGPDGuardrailEnforcement:
    """Tests for LGPD guardrail enforcement"""

    def test_art18_guardrail_blocks_non_compliant(self, non_compliant_output_no_explanation):
        """Test that Article 18 guardrail blocks non-compliant output"""
        with pytest.raises(ComplianceViolation) as exc_info:
            lgpd_art18_explanation_guardrail.enforce(non_compliant_output_no_explanation)

        violation = exc_info.value
        assert violation.guardrail.name == "lgpd_art18_explanation"
        assert violation.guardrail.regulation == "LGPD"
        assert violation.guardrail.severity == "block"
        assert not violation.result.passed

    def test_art18_guardrail_passes_compliant(self, compliant_output_art18):
        """Test that Article 18 guardrail passes compliant output"""
        enforced = lgpd_art18_explanation_guardrail.enforce(compliant_output_art18)

        assert enforced.original == compliant_output_art18
        assert enforced.validation_result.passed is True
        assert enforced.guardrail_name == "lgpd_art18_explanation"
        assert enforced.regulation == "LGPD"
        assert enforced.enforced is True

    def test_art20_guardrail_warns_non_compliant(self, non_compliant_output_no_format):
        """Test that Article 20 guardrail warns (doesn't block) on non-compliant output"""
        # Article 20 has severity="warn", so it should not raise exception
        enforced = lgpd_art20_portability_guardrail.enforce(non_compliant_output_no_format)

        assert enforced.validation_result.passed is False
        assert enforced.guardrail_name == "lgpd_art20_portability"
        assert enforced.regulation == "LGPD"
        # Should still be enforced (logged), just not blocked
        assert enforced.enforced is True

    def test_art20_guardrail_passes_compliant(self, compliant_output_art20):
        """Test that Article 20 guardrail passes compliant output"""
        enforced = lgpd_art20_portability_guardrail.enforce(compliant_output_art20)

        assert enforced.validation_result.passed is True
        assert enforced.guardrail_name == "lgpd_art20_portability"


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestLGPDConvenienceFunctions:
    """Tests for LGPD convenience functions"""

    def test_get_lgpd_guardrails(self):
        """Test getting all LGPD guardrails"""
        guardrails = get_lgpd_guardrails()

        assert len(guardrails) == 2
        assert any(g.name == "lgpd_art18_explanation" for g in guardrails)
        assert any(g.name == "lgpd_art20_portability" for g in guardrails)

    def test_get_guardrail_by_article_18(self):
        """Test getting Article 18 guardrail by number"""
        guardrail = get_lgpd_guardrail_by_article(18)

        assert guardrail.name == "lgpd_art18_explanation"
        assert guardrail.regulation == "LGPD"
        assert guardrail.severity == "block"

    def test_get_guardrail_by_article_20(self):
        """Test getting Article 20 guardrail by number"""
        guardrail = get_lgpd_guardrail_by_article(20)

        assert guardrail.name == "lgpd_art20_portability"
        assert guardrail.regulation == "LGPD"
        assert guardrail.severity == "warn"

    def test_get_guardrail_by_invalid_article(self):
        """Test that invalid article number raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            get_lgpd_guardrail_by_article(99)

        assert "not implemented" in str(exc_info.value).lower()

    def test_validate_with_lgpd(self, compliant_output_art18, compliant_output_art20):
        """Test batch validation with all LGPD guardrails"""
        # Test with output compliant for Art 18 but not Art 20
        results = validate_with_lgpd(compliant_output_art18)

        assert len(results) == 2
        # Should pass Art 18
        assert results[0].passed is True
        # Will fail Art 20 (no portability metadata)
        assert results[1].passed is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestLGPDIntegration:
    """Integration tests for LGPD guardrails"""

    def test_end_to_end_compliant_output(self):
        """Test end-to-end with fully compliant output"""
        output = AgentOutput(
            content='{"loan_decision": "approved", "amount": 50000}',
            has_explanation=True,
            explanation=(
                "Loan approved based on credit score (780), income ($85k/year), "
                "debt-to-income ratio (22%), and payment history (no late payments)."
            ),
            explanation_quality=0.85,
            metadata={
                "exportable_format": "json",
                "data_structure": {
                    "loan_decision": "string",
                    "amount": "integer"
                }
            },
            model_name="loan-decision-v1"
        )

        # Should pass both guardrails
        enforced_art18 = lgpd_art18_explanation_guardrail.enforce(output)
        assert enforced_art18.validation_result.passed is True

        enforced_art20 = lgpd_art20_portability_guardrail.enforce(output)
        assert enforced_art20.validation_result.passed is True

    def test_end_to_end_non_compliant_output(self):
        """Test end-to-end with non-compliant output"""
        output = AgentOutput(
            content="Loan denied",
            has_explanation=False,
            metadata=None,
            model_name="loan-decision-v1"
        )

        # Should fail Art 18 (blocking)
        with pytest.raises(ComplianceViolation):
            lgpd_art18_explanation_guardrail.enforce(output)

        # Should fail Art 20 but not block (warning)
        enforced_art20 = lgpd_art20_portability_guardrail.enforce(output)
        assert enforced_art20.validation_result.passed is False

    def test_multiple_guardrails_in_sequence(self, compliant_output_art18):
        """Test enforcing multiple guardrails in sequence"""
        # Get all LGPD guardrails
        guardrails = get_lgpd_guardrails()

        # Note: compliant_output_art18 doesn't have portability metadata
        # Art 18 should pass, Art 20 should warn

        for guardrail in guardrails:
            if guardrail.severity == "block":
                # May raise exception
                try:
                    enforced = guardrail.enforce(compliant_output_art18)
                    # If no exception, check it passed
                    if guardrail.name == "lgpd_art18_explanation":
                        assert enforced.validation_result.passed is True
                except ComplianceViolation:
                    pass
            else:
                # Should not raise exception (warn/audit)
                enforced = guardrail.enforce(compliant_output_art18)
                # Result may pass or fail, but shouldn't block
                assert enforced is not None
