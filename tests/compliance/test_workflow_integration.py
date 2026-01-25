"""
Integration Tests for SENTINEL with Temporal Workflows

Tests the integration of compliance guardrails with Temporal workflow activities.
"""

import pytest
from neutron.orchestration.workflows import (
    batch_validate_outputs_activity,
    validate_agent_output_activity,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def compliant_output():
    """Output that passes all LGPD guardrails"""
    return {
        "output_text": "Loan approved for $50,000 at 5.2% APR",
        "explanation": (
            "Loan approved based on the following criteria: "
            "credit score of 780 (excellent), annual income of $85,000, "
            "debt-to-income ratio of 22%, no late payments in last 24 months, "
            "and 8 years of credit history."
        ),
        "explanation_quality": 0.85,
        "metadata": {
            "exportable_format": "json",
            "data_structure": {"loan_amount": "float", "apr": "float", "approval_status": "string"},
        },
        "model_name": "loan-decision-v1",
    }


@pytest.fixture
def non_compliant_output_no_explanation():
    """Output that fails Article 18 (missing explanation)"""
    return {
        "output_text": "Loan denied",
        "explanation": None,
        "explanation_quality": 0.0,
        "metadata": None,
        "model_name": "loan-decision-v1",
    }


@pytest.fixture
def non_compliant_output_low_quality():
    """Output with low quality explanation"""
    return {
        "output_text": "Loan approved",
        "explanation": "Approved.",
        "explanation_quality": 0.3,
        "metadata": None,
        "model_name": "loan-decision-v1",
    }


@pytest.fixture
def warning_level_violation():
    """Output that passes Article 18 but fails Article 20 (warning only)"""
    return {
        "output_text": "Risk assessment complete",
        "explanation": (
            "Risk assessment based on credit score, income, "
            "debt-to-income ratio, and payment history."
        ),
        "explanation_quality": 0.85,
        "metadata": None,  # Missing portability info
        "model_name": "risk-assessment-v1",
    }


# =============================================================================
# Single Output Validation Tests
# =============================================================================


class TestValidateAgentOutputActivity:
    """Tests for validate_agent_output_activity"""

    @pytest.mark.asyncio
    async def test_compliant_output_passes(self, compliant_output):
        """Test that fully compliant output passes validation"""
        result = await validate_agent_output_activity(
            output_text=compliant_output["output_text"],
            explanation=compliant_output["explanation"],
            explanation_quality=compliant_output["explanation_quality"],
            metadata=compliant_output["metadata"],
            model_name=compliant_output["model_name"],
        )

        assert result["passed"] is True
        assert result["output"] == compliant_output["output_text"]
        assert result["blocked_by"] is None
        assert len(result["audit_ids"]) == 2  # Both LGPD guardrails
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_missing_explanation_blocks(self, non_compliant_output_no_explanation):
        """Test that missing explanation blocks output"""
        result = await validate_agent_output_activity(
            output_text=non_compliant_output_no_explanation["output_text"],
            explanation=non_compliant_output_no_explanation["explanation"],
            explanation_quality=non_compliant_output_no_explanation["explanation_quality"],
            metadata=non_compliant_output_no_explanation["metadata"],
            model_name=non_compliant_output_no_explanation["model_name"],
        )

        assert result["passed"] is False
        assert result["output"] is None
        assert result["blocked_by"] == "lgpd_art18_explanation"
        assert len(result["violations"]) > 0

        # Check violation details
        blocking_violation = result["violations"][0]
        assert blocking_violation["guardrail"] == "lgpd_art18_explanation"
        assert blocking_violation["severity"] == "block"
        assert blocking_violation["blocked"] is True
        assert "violation" in blocking_violation["details"].lower()

    @pytest.mark.asyncio
    async def test_low_quality_explanation_blocks(self, non_compliant_output_low_quality):
        """Test that low quality explanation blocks output"""
        result = await validate_agent_output_activity(
            output_text=non_compliant_output_low_quality["output_text"],
            explanation=non_compliant_output_low_quality["explanation"],
            explanation_quality=non_compliant_output_low_quality["explanation_quality"],
            metadata=non_compliant_output_low_quality["metadata"],
            model_name=non_compliant_output_low_quality["model_name"],
        )

        assert result["passed"] is False
        assert result["output"] is None
        assert result["blocked_by"] == "lgpd_art18_explanation"

    @pytest.mark.asyncio
    async def test_warning_level_violation_passes(self, warning_level_violation):
        """Test that warning-level violations don't block output"""
        result = await validate_agent_output_activity(
            output_text=warning_level_violation["output_text"],
            explanation=warning_level_violation["explanation"],
            explanation_quality=warning_level_violation["explanation_quality"],
            metadata=warning_level_violation["metadata"],
            model_name=warning_level_violation["model_name"],
        )

        # Should pass because Article 20 is warning-level
        assert result["passed"] is True
        assert result["output"] == warning_level_violation["output_text"]
        assert result["blocked_by"] is None

        # But should have warning violation logged
        assert len(result["violations"]) > 0
        warning = [v for v in result["violations"] if not v["blocked"]]
        assert len(warning) > 0
        assert warning[0]["guardrail"] == "lgpd_art20_portability"
        assert warning[0]["severity"] == "warn"

    @pytest.mark.asyncio
    async def test_specific_guardrail_enforcement(self, compliant_output):
        """Test enforcing only specific guardrails"""
        result = await validate_agent_output_activity(
            output_text=compliant_output["output_text"],
            explanation=compliant_output["explanation"],
            explanation_quality=compliant_output["explanation_quality"],
            metadata=compliant_output["metadata"],
            model_name=compliant_output["model_name"],
            guardrails=["lgpd_art18_explanation"],  # Only Article 18
        )

        assert result["passed"] is True
        # Should only have 1 audit ID (Article 18 only)
        assert len(result["audit_ids"]) == 1

    @pytest.mark.asyncio
    async def test_audit_ids_created(self, compliant_output):
        """Test that audit IDs are created for all guardrails"""
        result = await validate_agent_output_activity(
            output_text=compliant_output["output_text"],
            explanation=compliant_output["explanation"],
            explanation_quality=compliant_output["explanation_quality"],
            metadata=compliant_output["metadata"],
            model_name=compliant_output["model_name"],
        )

        # Should have audit IDs for both guardrails
        assert len(result["audit_ids"]) == 2
        # All audit IDs should be integers (database PKs)
        for audit_id in result["audit_ids"]:
            assert isinstance(audit_id, int)
            assert audit_id > 0


# =============================================================================
# Batch Validation Tests
# =============================================================================


class TestBatchValidateOutputsActivity:
    """Tests for batch_validate_outputs_activity"""

    @pytest.mark.asyncio
    async def test_batch_all_compliant(self, compliant_output):
        """Test batch validation with all compliant outputs"""
        outputs = [compliant_output.copy() for _ in range(3)]

        results = await batch_validate_outputs_activity(outputs)

        assert len(results) == 3
        for result in results:
            assert result["passed"] is True
            assert result["blocked_by"] is None

    @pytest.mark.asyncio
    async def test_batch_mixed_results(self, compliant_output, non_compliant_output_no_explanation):
        """Test batch validation with mixed compliant/non-compliant outputs"""
        outputs = [compliant_output, non_compliant_output_no_explanation, compliant_output.copy()]

        results = await batch_validate_outputs_activity(outputs)

        assert len(results) == 3
        assert results[0]["passed"] is True
        assert results[1]["passed"] is False
        assert results[2]["passed"] is True

        # Middle result should be blocked
        assert results[1]["blocked_by"] == "lgpd_art18_explanation"

    @pytest.mark.asyncio
    async def test_batch_all_non_compliant(self, non_compliant_output_no_explanation):
        """Test batch validation with all non-compliant outputs"""
        outputs = [non_compliant_output_no_explanation.copy() for _ in range(3)]

        results = await batch_validate_outputs_activity(outputs)

        assert len(results) == 3
        for result in results:
            assert result["passed"] is False
            assert result["blocked_by"] == "lgpd_art18_explanation"

    @pytest.mark.asyncio
    async def test_batch_with_specific_guardrails(self, compliant_output):
        """Test batch validation with specific guardrails"""
        outputs = [compliant_output.copy() for _ in range(2)]

        results = await batch_validate_outputs_activity(
            outputs, guardrails=["lgpd_art18_explanation"]
        )

        assert len(results) == 2
        for result in results:
            assert result["passed"] is True
            # Should only have 1 audit ID per output (Article 18 only)
            assert len(result["audit_ids"]) == 1


# =============================================================================
# Integration Scenario Tests
# =============================================================================


class TestWorkflowIntegrationScenarios:
    """Real-world integration scenarios"""

    @pytest.mark.asyncio
    async def test_ml_model_output_validation(self):
        """Test validating ML model output in workflow"""
        # Simulate ML model generating output with explanation
        model_output = {
            "output_text": (
                "Customer churn probability: 0.72 (HIGH RISK)\n"
                "Recommended action: Proactive retention offer"
            ),
            "explanation": (
                "Churn prediction based on: recent support tickets (5 in last month), "
                "decreased usage (-40% vs 3 months ago), late payment (1 instance), "
                "competitor activity in region (high), and tenure (18 months). "
                "Model confidence: 87%."
            ),
            "explanation_quality": 0.87,
            "metadata": {
                "exportable_format": "json",
                "data_structure": {
                    "churn_probability": "float",
                    "risk_level": "string",
                    "recommended_action": "string",
                    "model_confidence": "float",
                },
            },
            "model_name": "churn-predictor-v3",
        }

        result = await validate_agent_output_activity(**model_output)

        assert result["passed"] is True
        assert "Customer churn probability" in result["output"]

    @pytest.mark.asyncio
    async def test_ensemble_model_validation(self):
        """Test validating outputs from ensemble of models"""
        ensemble_outputs = [
            {
                "output_text": "Model A prediction: Approve",
                "explanation": "Approved based on credit score and income stability.",
                "explanation_quality": 0.75,
                "metadata": {
                    "exportable_format": "json",
                    "data_structure": {"prediction": "string"},
                },
                "model_name": "model-a",
            },
            {
                "output_text": "Model B prediction: Approve",
                "explanation": "Approved due to low debt-to-income ratio and good payment history.",
                "explanation_quality": 0.82,
                "metadata": {
                    "exportable_format": "json",
                    "data_structure": {"prediction": "string"},
                },
                "model_name": "model-b",
            },
            {
                "output_text": "Model C prediction: Deny",
                "explanation": None,  # This model doesn't provide explanations
                "explanation_quality": 0.0,
                "metadata": None,
                "model_name": "model-c",
            },
        ]

        results = await batch_validate_outputs_activity(ensemble_outputs)

        # First two should pass, third should fail
        assert results[0]["passed"] is True
        assert results[1]["passed"] is True
        assert results[2]["passed"] is False

        # Can use passing models for consensus, exclude non-compliant one
        compliant_models = [(i, r) for i, r in enumerate(results) if r["passed"]]
        assert len(compliant_models) == 2

    @pytest.mark.asyncio
    async def test_retry_after_violation(self):
        """Test workflow retry after compliance violation"""
        # First attempt - no explanation
        attempt1 = {
            "output_text": "Credit limit increase denied",
            "explanation": None,
            "explanation_quality": 0.0,
            "metadata": None,
            "model_name": "credit-limit-v1",
        }

        result1 = await validate_agent_output_activity(**attempt1)
        assert result1["passed"] is False
        assert result1["blocked_by"] == "lgpd_art18_explanation"

        # Second attempt - with explanation (simulating agent regeneration)
        attempt2 = {
            "output_text": "Credit limit increase denied",
            "explanation": (
                "Credit limit increase denied due to: "
                "current utilization at 85% (high), "
                "recent missed payment (1 in last 90 days), "
                "and short credit history (2 years)."
            ),
            "explanation_quality": 0.80,
            "metadata": {
                "exportable_format": "json",
                "data_structure": {"decision": "string", "current_utilization": "float"},
            },
            "model_name": "credit-limit-v1",
        }

        result2 = await validate_agent_output_activity(**attempt2)
        assert result2["passed"] is True
        assert "denied due to" in result2["output"]
