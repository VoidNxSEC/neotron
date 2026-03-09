"""
Tests for GDPR Compliance Auditors

Tests GDPR Articles 22, 15, and 17 compliance guardrails.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from neutron.compliance.auditors.gdpr import (
    GDPR_GUARDRAILS,
    # Erasure handler
    GDPRErasureHandler,
    # Article 15 - Right to Access
    check_gdpr_article_15_data_access,
    # Article 17 - Right to Erasure
    check_gdpr_article_17_erasure_support,
    # Article 22 - Human Oversight
    check_gdpr_article_22_human_oversight,
    gdpr_art15_data_access_guardrail,
    gdpr_art17_erasure_support_guardrail,
    gdpr_art22_human_oversight_guardrail,
    get_gdpr_guardrail_by_article,
    # Convenience functions
    get_gdpr_guardrails,
    validate_with_gdpr,
)
from neutron.compliance.sentinel import (
    AgentOutput,
    ComplianceViolation,
    ValidationResult,
)

# =============================================================================
# GDPR Article 22 - Automated Decision-Making & Human Oversight
# =============================================================================


class TestGDPRArticle22HumanOversight:
    """Tests for GDPR Article 22 compliance"""

    def test_low_risk_decision_passes(self):
        """Low-risk automated decisions don't require human oversight"""
        output = AgentOutput(
            content="Recommendation: Consider diversifying portfolio",
            metadata={"risk_level": "low"},
        )

        result = check_gdpr_article_22_human_oversight(output)

        assert result.passed is True
        assert "low-risk" in result.details.lower()
        assert result.confidence == 1.0
        assert result.metadata["risk_level"] == "low"

    def test_high_risk_without_human_review_fails(self):
        """High-risk decisions require human oversight"""
        output = AgentOutput(
            content="Loan application denied",
            metadata={"risk_level": "high", "human_reviewed": False},
        )

        result = check_gdpr_article_22_human_oversight(output)

        assert result.passed is False
        assert "human oversight" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_human_review"
        assert result.metadata["risk_level"] == "high"

    def test_medium_risk_without_human_review_fails(self):
        """Medium-risk decisions also require human oversight"""
        output = AgentOutput(
            content="Credit limit reduced",
            metadata={"risk_level": "medium", "human_reviewed": False},
        )

        result = check_gdpr_article_22_human_oversight(output)

        assert result.passed is False
        assert "human oversight" in result.details.lower()
        assert result.metadata["risk_level"] == "medium"

    def test_high_risk_missing_reviewer_id_fails(self):
        """Human review requires reviewer identification"""
        output = AgentOutput(
            content="Insurance claim approved",
            metadata={
                "risk_level": "high",
                "human_reviewed": True,
                # Missing reviewer_id
                "review_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        result = check_gdpr_article_22_human_oversight(output)

        assert result.passed is False
        assert "reviewer id" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_reviewer_id"
        assert result.confidence == 0.9

    def test_high_risk_missing_review_timestamp_fails(self):
        """Human review requires timestamp"""
        output = AgentOutput(
            content="Insurance claim approved",
            metadata={
                "risk_level": "high",
                "human_reviewed": True,
                "reviewer_id": "reviewer_001",
                # Missing review_timestamp
            },
        )

        result = check_gdpr_article_22_human_oversight(output)

        assert result.passed is False
        assert "timestamp" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_review_timestamp"
        assert result.confidence == 0.9

    def test_high_risk_with_complete_review_passes(self):
        """High-risk decision with complete human review passes"""
        timestamp = datetime.now(timezone.utc).isoformat()
        output = AgentOutput(
            content="Loan approved after review",
            metadata={
                "risk_level": "high",
                "human_reviewed": True,
                "reviewer_id": "reviewer_001",
                "review_timestamp": timestamp,
            },
        )

        result = check_gdpr_article_22_human_oversight(output)

        assert result.passed is True
        assert "compliant" in result.details.lower()
        assert result.metadata["reviewer_id"] == "reviewer_001"
        assert result.metadata["review_timestamp"] == timestamp
        assert result.confidence == 1.0

    def test_unknown_risk_level_fails(self):
        """Unknown risk levels should fail (fail-safe)"""
        output = AgentOutput(content="Decision made", metadata={"risk_level": "super-duper-high"})

        result = check_gdpr_article_22_human_oversight(output)

        assert result.passed is False
        assert "unknown risk level" in result.details.lower()
        assert result.metadata["violation_type"] == "invalid_risk_level"
        assert result.metadata["provided_risk_level"] == "super-duper-high"

    def test_missing_metadata_fails(self):
        """Missing metadata should fail"""
        output = AgentOutput(content="Decision made", metadata=None)

        result = check_gdpr_article_22_human_oversight(output)

        assert result.passed is False
        assert "no metadata" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_metadata"


# =============================================================================
# GDPR Article 15 - Right to Access
# =============================================================================


class TestGDPRArticle15DataAccess:
    """Tests for GDPR Article 15 compliance"""

    def test_complete_data_access_passes(self):
        """Complete data access configuration passes"""
        output = AgentOutput(
            content="Customer data processed",
            metadata={
                "data_access_enabled": True,
                "data_categories": ["name", "email", "preferences"],
                "retention_period": "90 days",
                "export_format": "JSON",
            },
        )

        result = check_gdpr_article_15_data_access(output)

        assert result.passed is True
        assert "compliant" in result.details.lower()
        assert result.metadata["data_categories"] == ["name", "email", "preferences"]
        assert result.metadata["retention_period"] == "90 days"
        assert result.metadata["export_format"] == "JSON"
        assert result.confidence == 1.0

    def test_missing_metadata_fails(self):
        """Missing metadata fails Article 15"""
        output = AgentOutput(content="Data processed", metadata=None)

        result = check_gdpr_article_15_data_access(output)

        assert result.passed is False
        assert "no metadata" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_metadata"

    def test_data_access_disabled_fails(self):
        """Disabled data access fails"""
        output = AgentOutput(content="Data processed", metadata={"data_access_enabled": False})

        result = check_gdpr_article_15_data_access(output)

        assert result.passed is False
        assert "data access must be enabled" in result.details.lower()
        assert result.metadata["violation_type"] == "access_disabled"
        assert result.confidence == 1.0

    def test_missing_data_categories_fails(self):
        """Missing data categories fails"""
        output = AgentOutput(
            content="Data processed",
            metadata={
                "data_access_enabled": True,
                # Missing data_categories
                "retention_period": "90 days",
                "export_format": "JSON",
            },
        )

        result = check_gdpr_article_15_data_access(output)

        assert result.passed is False
        assert "data categories" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_categories"
        assert result.confidence == 0.9

    def test_missing_retention_period_fails(self):
        """Missing retention period fails"""
        output = AgentOutput(
            content="Data processed",
            metadata={
                "data_access_enabled": True,
                "data_categories": ["name", "email"],
                # Missing retention_period
                "export_format": "JSON",
            },
        )

        result = check_gdpr_article_15_data_access(output)

        assert result.passed is False
        assert "retention period" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_retention"
        assert result.confidence == 0.8

    def test_missing_export_format_fails(self):
        """Missing export format fails"""
        output = AgentOutput(
            content="Data processed",
            metadata={
                "data_access_enabled": True,
                "data_categories": ["name", "email"],
                "retention_period": "90 days",
                # Missing export_format
            },
        )

        result = check_gdpr_article_15_data_access(output)

        assert result.passed is False
        assert "export format" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_export_format"
        assert result.confidence == 0.8


# =============================================================================
# GDPR Article 17 - Right to Erasure
# =============================================================================


class TestGDPRArticle17ErasureSupport:
    """Tests for GDPR Article 17 compliance"""

    def test_no_metadata_passes(self):
        """No metadata means no personal data, should pass"""
        output = AgentOutput(content="Generic response", metadata=None)

        result = check_gdpr_article_17_erasure_support(output)

        assert result.passed is True
        assert "not applicable" in result.details.lower()
        assert result.confidence == 1.0

    def test_no_personal_data_passes(self):
        """No personal data means no erasure requirement"""
        output = AgentOutput(
            content="Generic response", metadata={"processes_personal_data": False}
        )

        result = check_gdpr_article_17_erasure_support(output)

        assert result.passed is True
        assert "no personal data" in result.details.lower()
        assert result.confidence == 1.0

    def test_personal_data_with_erasure_support_passes(self):
        """Personal data with erasure support passes"""
        output = AgentOutput(
            content="Customer profile updated",
            metadata={
                "processes_personal_data": True,
                "erasure_supported": True,
                "erasure_endpoint": "/api/v1/customers/{id}/delete",
            },
        )

        result = check_gdpr_article_17_erasure_support(output)

        assert result.passed is True
        assert "compliant" in result.details.lower()
        assert result.metadata["erasure_endpoint"] == "/api/v1/customers/{id}/delete"
        assert result.confidence == 1.0

    def test_personal_data_without_erasure_support_fails(self):
        """Personal data without erasure support fails"""
        output = AgentOutput(
            content="Customer data stored",
            metadata={"processes_personal_data": True, "erasure_supported": False},
        )

        result = check_gdpr_article_17_erasure_support(output)

        assert result.passed is False
        assert "erasure must be supported" in result.details.lower()
        assert result.metadata["violation_type"] == "erasure_not_supported"
        assert result.confidence == 1.0

    def test_missing_erasure_endpoint_fails(self):
        """Missing erasure endpoint fails"""
        output = AgentOutput(
            content="Customer data stored",
            metadata={
                "processes_personal_data": True,
                "erasure_supported": True,
                # Missing erasure_endpoint
            },
        )

        result = check_gdpr_article_17_erasure_support(output)

        assert result.passed is False
        assert "erasure endpoint" in result.details.lower()
        assert result.metadata["violation_type"] == "missing_endpoint"
        assert result.confidence == 0.9


# =============================================================================
# Pre-configured Guardrails
# =============================================================================


class TestGDPRGuardrails:
    """Tests for pre-configured GDPR guardrails"""

    def test_article_22_guardrail_blocks_high_risk_without_review(self):
        """Article 22 guardrail blocks high-risk decisions without review"""
        output = AgentOutput(
            content="Loan denied", metadata={"risk_level": "high", "human_reviewed": False}
        )

        with pytest.raises(ComplianceViolation) as exc_info:
            gdpr_art22_human_oversight_guardrail.enforce(output)

        assert exc_info.value.guardrail.name == "gdpr_art22_human_oversight"
        assert exc_info.value.guardrail.regulation == "GDPR"
        assert exc_info.value.result.passed is False

    def test_article_22_guardrail_allows_low_risk(self):
        """Article 22 guardrail allows low-risk decisions"""
        output = AgentOutput(content="Recommendation provided", metadata={"risk_level": "low"})

        # Should not raise exception
        enforced = gdpr_art22_human_oversight_guardrail.enforce(output)
        assert enforced.original == output
        assert enforced.enforced is True

    def test_article_15_guardrail_warns_on_violation(self):
        """Article 15 guardrail warns but doesn't block"""
        output = AgentOutput(content="Data processed", metadata={"data_access_enabled": False})

        # Should not raise (warn severity)
        enforced = gdpr_art15_data_access_guardrail.enforce(output)
        assert enforced.original == output
        assert enforced.enforced is True

    def test_article_17_guardrail_warns_on_violation(self):
        """Article 17 guardrail warns but doesn't block"""
        output = AgentOutput(
            content="Data stored",
            metadata={"processes_personal_data": True, "erasure_supported": False},
        )

        # Should not raise (warn severity)
        enforced = gdpr_art17_erasure_support_guardrail.enforce(output)
        assert enforced.original == output
        assert enforced.enforced is True

    def test_gdpr_guardrails_list(self):
        """GDPR_GUARDRAILS contains all three guardrails"""
        assert len(GDPR_GUARDRAILS) == 3

        guardrail_names = [g.name for g in GDPR_GUARDRAILS]
        assert "gdpr_art22_human_oversight" in guardrail_names
        assert "gdpr_art15_data_access" in guardrail_names
        assert "gdpr_art17_erasure_support" in guardrail_names

        # Check regulations
        assert all(g.regulation == "GDPR" for g in GDPR_GUARDRAILS)

        # Check severities
        severities = {g.name: g.severity for g in GDPR_GUARDRAILS}
        assert severities["gdpr_art22_human_oversight"] == "block"
        assert severities["gdpr_art15_data_access"] == "warn"
        assert severities["gdpr_art17_erasure_support"] == "warn"


# =============================================================================
# Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_get_gdpr_guardrails(self):
        """get_gdpr_guardrails returns all GDPR guardrails"""
        guardrails = get_gdpr_guardrails()

        assert len(guardrails) == 3
        assert all(g.regulation == "GDPR" for g in guardrails)

        # Should be a copy
        assert guardrails is not GDPR_GUARDRAILS

    def test_get_gdpr_guardrail_by_article_22(self):
        """get_gdpr_guardrail_by_article returns Article 22"""
        guardrail = get_gdpr_guardrail_by_article(22)

        assert guardrail.name == "gdpr_art22_human_oversight"
        assert guardrail.regulation == "GDPR"
        assert guardrail.severity == "block"

    def test_get_gdpr_guardrail_by_article_15(self):
        """get_gdpr_guardrail_by_article returns Article 15"""
        guardrail = get_gdpr_guardrail_by_article(15)

        assert guardrail.name == "gdpr_art15_data_access"
        assert guardrail.regulation == "GDPR"
        assert guardrail.severity == "warn"

    def test_get_gdpr_guardrail_by_article_17(self):
        """get_gdpr_guardrail_by_article returns Article 17"""
        guardrail = get_gdpr_guardrail_by_article(17)

        assert guardrail.name == "gdpr_art17_erasure_support"
        assert guardrail.regulation == "GDPR"
        assert guardrail.severity == "warn"

    def test_get_gdpr_guardrail_by_article_invalid(self):
        """get_gdpr_guardrail_by_article raises ValueError for invalid article"""
        with pytest.raises(ValueError, match="not implemented"):
            get_gdpr_guardrail_by_article(99)

        with pytest.raises(ValueError, match="Available articles: \\[15, 17, 22\\]"):
            get_gdpr_guardrail_by_article(5)

    def test_validate_with_gdpr_all_pass(self):
        """validate_with_gdpr returns results for all guardrails"""
        output = AgentOutput(
            content="Compliant output",
            metadata={
                "risk_level": "low",
                "data_access_enabled": True,
                "data_categories": ["name"],
                "retention_period": "90 days",
                "export_format": "JSON",
                "processes_personal_data": True,
                "erasure_supported": True,
                "erasure_endpoint": "/api/delete",
            },
        )

        results = validate_with_gdpr(output)

        assert len(results) == 3
        assert all(isinstance(r, ValidationResult) for r in results)
        assert all(r.passed for r in results)

    def test_validate_with_gdpr_some_fail(self):
        """validate_with_gdpr shows failures without enforcing"""
        output = AgentOutput(
            content="Non-compliant output",
            metadata={
                "risk_level": "high",
                "human_reviewed": False,
                "data_access_enabled": False,
                "processes_personal_data": True,
                "erasure_supported": False,
            },
        )

        results = validate_with_gdpr(output)

        assert len(results) == 3

        # Article 22 should fail
        art22_result = next(r for r in results if "Article 22" in r.metadata.get("article", ""))
        assert art22_result.passed is False

        # Article 15 should fail
        art15_result = next(r for r in results if "Article 15" in r.metadata.get("article", ""))
        assert art15_result.passed is False

        # Article 17 should fail
        art17_result = next(r for r in results if "Article 17" in r.metadata.get("article", ""))
        assert art17_result.passed is False


# =============================================================================
# GDPRErasureHandler Integration Tests
# =============================================================================


class TestGDPRErasureHandler:
    """Tests for GDPR erasure handler"""

    @patch("neutron.memory.MemoryStore")
    @patch("neutron.compliance.audit_logger.AuditLogger")
    def test_erase_customer_data(self, mock_audit_logger_class, mock_memory_store_class):
        """Test erasing customer data"""
        # Mock MemoryStore
        mock_memory_store = MagicMock()
        mock_memory_store.delete_by_customer.return_value = 5
        mock_memory_store_class.return_value = mock_memory_store

        # Mock AuditLogger
        mock_logger = MagicMock()
        mock_logger.log.return_value = "audit_123"
        mock_audit_logger_class.return_value = mock_logger

        # Create handler without memory_store (will create one)
        handler = GDPRErasureHandler()

        # Erase customer data
        result = handler.erase_customer_data("customer_456")

        # Verify MemoryStore was called
        mock_memory_store.delete_by_customer.assert_called_once_with("customer_456")

        # Verify audit log was created
        assert mock_logger.log.called
        log_call = mock_logger.log.call_args[0][0]
        assert log_call["event"] == "gdpr_art17_erasure"
        assert log_call["regulation"] == "GDPR"
        assert log_call["customer_id"] == "customer_456"
        assert log_call["deleted_memories"] == 5
        assert log_call["article"] == "GDPR Article 17"

        # Verify result
        assert result["customer_id"] == "customer_456"
        assert result["deleted_memories"] == 5
        assert result["audit_id"] == "audit_123"
        assert result["status"] == "completed"

    @patch("neutron.compliance.audit_logger.AuditLogger")
    def test_erase_customer_data_with_provided_memory_store(self, mock_audit_logger_class):
        """Test erasure with provided memory store"""
        # Mock MemoryStore
        mock_memory_store = MagicMock()
        mock_memory_store.delete_by_customer.return_value = 3

        # Mock AuditLogger
        mock_logger = MagicMock()
        mock_logger.log.return_value = "audit_789"
        mock_audit_logger_class.return_value = mock_logger

        # Create handler with memory_store
        handler = GDPRErasureHandler(memory_store=mock_memory_store)

        # Erase customer data
        result = handler.erase_customer_data("customer_789")

        # Verify provided memory store was used
        mock_memory_store.delete_by_customer.assert_called_once_with("customer_789")

        # Verify result
        assert result["deleted_memories"] == 3
        assert result["status"] == "completed"


# =============================================================================
# Integration Tests
# =============================================================================


class TestGDPRIntegration:
    """Integration tests for GDPR compliance"""

    def test_compliant_workflow(self):
        """Test fully compliant workflow"""
        # Low-risk decision with data access
        output = AgentOutput(
            content="Portfolio recommendation generated",
            metadata={
                "risk_level": "low",
                "data_access_enabled": True,
                "data_categories": ["preferences", "risk_tolerance"],
                "retention_period": "180 days",
                "export_format": "JSON",
                "processes_personal_data": True,
                "erasure_supported": True,
                "erasure_endpoint": "/api/customers/{id}/delete",
            },
        )

        # Validate with all GDPR guardrails
        results = validate_with_gdpr(output)

        assert all(r.passed for r in results)

    def test_high_risk_workflow_with_review(self):
        """Test high-risk decision with proper human review"""
        timestamp = datetime.now(timezone.utc).isoformat()
        output = AgentOutput(
            content="Loan approved",
            metadata={
                "risk_level": "high",
                "human_reviewed": True,
                "reviewer_id": "compliance_officer_001",
                "review_timestamp": timestamp,
                "data_access_enabled": True,
                "data_categories": ["financial_data", "credit_score"],
                "retention_period": "7 years",
                "export_format": "PDF",
                "processes_personal_data": True,
                "erasure_supported": True,
                "erasure_endpoint": "/api/loans/{id}/delete",
            },
        )

        # All guardrails should pass
        results = validate_with_gdpr(output)
        assert all(r.passed for r in results)

        # Article 22 should not block
        enforced = gdpr_art22_human_oversight_guardrail.enforce(output)
        assert enforced.original == output
        assert enforced.enforced is True

    def test_non_compliant_high_risk_blocks(self):
        """Test non-compliant high-risk decision blocks"""
        output = AgentOutput(
            content="Credit denied", metadata={"risk_level": "high", "human_reviewed": False}
        )

        # Article 22 should block
        with pytest.raises(ComplianceViolation):
            gdpr_art22_human_oversight_guardrail.enforce(output)

    def test_erasure_integration(self):
        """Test erasure handler integration"""
        with patch("neutron.memory.MemoryStore") as mock_store_class:
            with patch("neutron.compliance.audit_logger.AuditLogger") as mock_logger_class:
                # Setup mocks
                mock_store = MagicMock()
                mock_store.delete_by_customer.return_value = 10
                mock_store_class.return_value = mock_store

                mock_logger = MagicMock()
                mock_logger.log.return_value = "audit_erasure_001"
                mock_logger_class.return_value = mock_logger

                # Execute erasure
                handler = GDPRErasureHandler()
                result = handler.erase_customer_data("gdpr_customer_001")

                # Verify
                assert result["deleted_memories"] == 10
                assert result["status"] == "completed"
                assert "audit_id" in result
