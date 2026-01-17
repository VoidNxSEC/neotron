"""
Tests for EU AI Act Compliance Auditors

Tests risk classification, transparency requirements (Article 13),
human oversight (Article 14), and prohibited practices (Article 5).
"""

import pytest
from neutron.compliance.sentinel import AgentOutput, ValidationResult
from neutron.compliance.auditors.ai_act import (
    AISystemRiskLevel,
    classify_ai_system_risk,
    check_ai_act_article_13_transparency,
    check_ai_act_article_14_human_oversight,
    check_ai_act_prohibited_practices,
    ARTICLE_13_TRANSPARENCY,
    ARTICLE_14_HUMAN_OVERSIGHT,
    ARTICLE_5_PROHIBITED_PRACTICES,
    get_ai_act_guardrails,
    validate_ai_act_compliance,
)


# =============================================================================
# Risk Classification Tests
# =============================================================================


class TestRiskClassification:
    """Tests for AI system risk classification"""

    def test_classify_unacceptable_risk_social_scoring(self):
        """Test that social scoring is classified as unacceptable"""
        risk = classify_ai_system_risk("social_scoring_system")
        assert risk == AISystemRiskLevel.UNACCEPTABLE

    def test_classify_unacceptable_risk_biometric_surveillance(self):
        """Test that real-time biometric surveillance is unacceptable"""
        risk = classify_ai_system_risk("real_time_biometric_surveillance")
        assert risk == AISystemRiskLevel.UNACCEPTABLE

    def test_classify_high_risk_loan_approval(self):
        """Test that loan approval is high-risk"""
        risk = classify_ai_system_risk("loan_approval")
        assert risk == AISystemRiskLevel.HIGH

    def test_classify_high_risk_employment(self):
        """Test that employment decisions are high-risk"""
        risk = classify_ai_system_risk("recruitment_screening")
        assert risk == AISystemRiskLevel.HIGH

    def test_classify_high_risk_biometric(self):
        """Test that biometric systems are high-risk"""
        risk = classify_ai_system_risk("facial_recognition_access")
        assert risk == AISystemRiskLevel.HIGH

    def test_classify_high_risk_education(self):
        """Test that education decisions are high-risk"""
        risk = classify_ai_system_risk("student_evaluation_system")
        assert risk == AISystemRiskLevel.HIGH

    def test_classify_high_risk_law_enforcement(self):
        """Test that law enforcement AI is high-risk"""
        risk = classify_ai_system_risk("crime_prediction_tool")
        assert risk == AISystemRiskLevel.HIGH

    def test_classify_high_risk_critical_infrastructure(self):
        """Test that critical infrastructure is high-risk"""
        risk = classify_ai_system_risk("electricity_grid_management")
        assert risk == AISystemRiskLevel.HIGH

    def test_classify_limited_risk_chatbot(self):
        """Test that chatbots are limited risk"""
        risk = classify_ai_system_risk("customer_service_chatbot")
        assert risk == AISystemRiskLevel.LIMITED

    def test_classify_limited_risk_deepfake(self):
        """Test that deepfake generation is limited risk"""
        risk = classify_ai_system_risk("deepfake_generator")
        assert risk == AISystemRiskLevel.LIMITED

    def test_classify_minimal_risk_spam_filter(self):
        """Test that spam filters are minimal risk"""
        risk = classify_ai_system_risk("email_spam_filter")
        assert risk == AISystemRiskLevel.MINIMAL

    def test_classify_minimal_risk_recommendation(self):
        """Test that product recommendations are minimal risk"""
        risk = classify_ai_system_risk("product_suggestions")
        assert risk == AISystemRiskLevel.MINIMAL

    def test_classify_with_metadata(self):
        """Test risk classification with additional metadata"""
        risk = classify_ai_system_risk(
            "decision_system",
            metadata={"sector": "financial_services", "impact": "high"}
        )
        # Should still classify based on use_case if no keywords match
        assert risk == AISystemRiskLevel.MINIMAL


# =============================================================================
# Article 13 - Transparency Tests
# =============================================================================


class TestArticle13Transparency:
    """Tests for EU AI Act Article 13 transparency requirements"""

    def test_transparency_no_metadata(self):
        """Test that missing metadata fails transparency check"""
        output = AgentOutput(
            content="Decision made",
            metadata=None
        )
        result = check_ai_act_article_13_transparency(output)

        assert not result.passed
        assert "Article 13" in result.details
        assert "No metadata" in result.details

    def test_transparency_missing_ai_disclosure(self):
        """Test that missing AI disclosure fails"""
        output = AgentOutput(
            content="Decision",
            metadata={"other_field": "value"}
        )
        result = check_ai_act_article_13_transparency(output)

        assert not result.passed
        assert "ai_disclosure" in result.details.lower()

    def test_transparency_missing_system_info(self):
        """Test that missing system info fails"""
        output = AgentOutput(
            content="Decision",
            metadata={"ai_disclosure": True}
        )
        result = check_ai_act_article_13_transparency(output)

        assert not result.passed
        assert "system_info" in result.details.lower()

    def test_transparency_minimal_risk_compliant(self):
        """Test that minimal risk system with basic disclosure passes"""
        output = AgentOutput(
            content="Spam detected",
            metadata={
                "ai_disclosure": True,
                "system_info": "AI spam detection system",
                "use_case": "spam_filter"
            }
        )
        result = check_ai_act_article_13_transparency(output)

        assert result.passed
        assert "minimal" in result.details.lower()

    def test_transparency_high_risk_missing_capabilities(self):
        """Test that high-risk system without capabilities fails"""
        output = AgentOutput(
            content="Loan approved",
            metadata={
                "ai_disclosure": True,
                "system_info": "AI credit scoring system",
                "use_case": "loan_approval"
            }
        )
        result = check_ai_act_article_13_transparency(output)

        assert not result.passed
        assert "capabilities" in result.details.lower()

    def test_transparency_high_risk_missing_limitations(self):
        """Test that high-risk system without limitations fails"""
        output = AgentOutput(
            content="Loan approved",
            metadata={
                "ai_disclosure": True,
                "system_info": "AI credit scoring",
                "use_case": "loan_approval",
                "capabilities": "Evaluates creditworthiness based on history"
            }
        )
        result = check_ai_act_article_13_transparency(output)

        assert not result.passed
        assert "limitations" in result.details.lower()

    def test_transparency_high_risk_compliant(self):
        """Test that high-risk system with full disclosure passes"""
        output = AgentOutput(
            content="Loan approved",
            metadata={
                "ai_disclosure": True,
                "system_info": "AI credit scoring system v2.1",
                "use_case": "loan_approval",
                "capabilities": "Evaluates creditworthiness using 50+ financial indicators",
                "limitations": "Does not account for recent life events or non-financial factors"
            }
        )
        result = check_ai_act_article_13_transparency(output)

        assert result.passed
        assert "high" in result.details.lower()
        assert "compliant" in result.details.lower()

    def test_transparency_synthetic_content_missing_warning(self):
        """Test that synthetic content without warning fails"""
        output = AgentOutput(
            content="Generated text",
            metadata={
                "ai_disclosure": True,
                "system_info": "Text generation AI",
                "use_case": "content_generation",
                "synthetic_content": True
            }
        )
        result = check_ai_act_article_13_transparency(output)

        assert not result.passed
        assert "synthetic_content_warning" in result.details.lower()

    def test_transparency_synthetic_content_with_warning(self):
        """Test that synthetic content with warning passes"""
        output = AgentOutput(
            content="Generated text",
            metadata={
                "ai_disclosure": True,
                "system_info": "AI content generator",
                "use_case": "content_generation",
                "synthetic_content": True,
                "synthetic_content_warning": "This content was generated by AI"
            }
        )
        result = check_ai_act_article_13_transparency(output)

        assert result.passed

    def test_transparency_limited_risk_chatbot(self):
        """Test transparency for limited-risk chatbot"""
        output = AgentOutput(
            content="How can I help you?",
            metadata={
                "ai_disclosure": True,
                "system_info": "Customer service AI assistant",
                "use_case": "chatbot"
            }
        )
        result = check_ai_act_article_13_transparency(output)

        assert result.passed
        assert "limited" in result.details.lower()


# =============================================================================
# Article 14 - Human Oversight Tests
# =============================================================================


class TestArticle14HumanOversight:
    """Tests for EU AI Act Article 14 human oversight requirements"""

    def test_oversight_no_metadata(self):
        """Test that missing metadata fails oversight check"""
        output = AgentOutput(
            content="Decision",
            metadata=None
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert not result.passed
        assert "Article 14" in result.details

    def test_oversight_minimal_risk_not_required(self):
        """Test that minimal risk systems don't require oversight"""
        output = AgentOutput(
            content="Spam",
            metadata={"use_case": "spam_filter"}
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert result.passed
        assert "oversight not required" in result.details.lower()

    def test_oversight_limited_risk_not_required(self):
        """Test that limited risk systems don't require oversight"""
        output = AgentOutput(
            content="Response",
            metadata={"use_case": "chatbot"}
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert result.passed
        assert "oversight not required" in result.details.lower()

    def test_oversight_high_risk_oversight_disabled(self):
        """Test that high-risk system without oversight fails"""
        output = AgentOutput(
            content="Loan approved",
            metadata={
                "use_case": "loan_approval",
                "human_oversight_enabled": False
            }
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert not result.passed
        assert "requires human oversight" in result.details.lower()

    def test_oversight_high_risk_missing_mechanism(self):
        """Test that high-risk system without mechanism fails"""
        output = AgentOutput(
            content="Hire candidate",
            metadata={
                "use_case": "recruitment",
                "human_oversight_enabled": True
            }
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert not result.passed
        assert "oversight_mechanism" in result.details.lower()

    def test_oversight_high_risk_invalid_mechanism(self):
        """Test that invalid oversight mechanism fails"""
        output = AgentOutput(
            content="Decision",
            metadata={
                "use_case": "credit_score",
                "human_oversight_enabled": True,
                "oversight_mechanism": "invalid_mechanism"
            }
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert not result.passed
        assert "Invalid or missing oversight mechanism" in result.details

    def test_oversight_high_risk_missing_overseer_id(self):
        """Test that missing overseer ID fails"""
        output = AgentOutput(
            content="Decision",
            metadata={
                "use_case": "loan",
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_in_the_loop"
            }
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert not result.passed
        assert "overseer_id" in result.details.lower()

    def test_oversight_high_risk_cannot_override(self):
        """Test that missing override capability fails"""
        output = AgentOutput(
            content="Decision",
            metadata={
                "use_case": "employment",
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_on_the_loop",
                "overseer_id": "reviewer_123"
            }
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert not result.passed
        assert "override" in result.details.lower()

    def test_oversight_high_risk_human_in_loop_compliant(self):
        """Test compliant human-in-the-loop oversight"""
        output = AgentOutput(
            content="Loan approved",
            metadata={
                "use_case": "loan_approval",
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_in_the_loop",
                "overseer_id": "loan_officer_456",
                "can_override": True
            }
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert result.passed
        assert "human_in_the_loop" in result.details

    def test_oversight_high_risk_human_on_loop_compliant(self):
        """Test compliant human-on-the-loop oversight"""
        output = AgentOutput(
            content="Risk assessment: medium",
            metadata={
                "use_case": "credit",
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_on_the_loop",
                "overseer_id": "risk_manager_789",
                "can_override": True
            }
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert result.passed
        assert "human_on_the_loop" in result.details

    def test_oversight_human_in_command_missing_authority(self):
        """Test that human-in-command without decision authority fails"""
        output = AgentOutput(
            content="Hiring decision",
            metadata={
                "use_case": "recruitment",
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_in_command",
                "overseer_id": "hr_manager_101",
                "can_override": True
            }
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert not result.passed
        assert "human_decision_authority" in result.details.lower()

    def test_oversight_human_in_command_compliant(self):
        """Test compliant human-in-command oversight"""
        output = AgentOutput(
            content="Candidate recommended",
            metadata={
                "use_case": "hiring",
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_in_command",
                "overseer_id": "hiring_manager_202",
                "can_override": True,
                "human_decision_authority": True
            }
        )
        result = check_ai_act_article_14_human_oversight(output)

        assert result.passed
        assert "human_in_command" in result.details


# =============================================================================
# Article 5 - Prohibited Practices Tests
# =============================================================================


class TestArticle5ProhibitedPractices:
    """Tests for EU AI Act Article 5 prohibited practices"""

    def test_prohibited_no_metadata(self):
        """Test prohibited practices check without metadata"""
        output = AgentOutput(
            content="Decision",
            metadata=None
        )
        result = check_ai_act_prohibited_practices(output)

        # Should pass but with warning
        assert result.passed
        assert result.confidence == 0.5

    def test_prohibited_social_scoring(self):
        """Test that social scoring is blocked"""
        output = AgentOutput(
            content="Citizen score: 650/1000",
            metadata={"use_case": "social_scoring"}
        )
        result = check_ai_act_prohibited_practices(output)

        assert not result.passed
        assert "PROHIBITED" in result.details.upper() or "BANNED" in result.details.upper()
        assert "unacceptable" in result.details.lower()

    def test_prohibited_biometric_surveillance(self):
        """Test that real-time biometric surveillance is blocked"""
        output = AgentOutput(
            content="Person identified",
            metadata={"use_case": "real_time_biometric_surveillance"}
        )
        result = check_ai_act_prohibited_practices(output)

        assert not result.passed
        assert "Article 5" in result.details

    def test_prohibited_subliminal_manipulation(self):
        """Test that subliminal manipulation is blocked"""
        output = AgentOutput(
            content="Influence applied",
            metadata={"use_case": "subliminal_manipulation"}
        )
        result = check_ai_act_prohibited_practices(output)

        assert not result.passed

    def test_prohibited_high_risk_allowed(self):
        """Test that high-risk (but not prohibited) systems pass"""
        output = AgentOutput(
            content="Loan approved",
            metadata={"use_case": "loan_approval"}
        )
        result = check_ai_act_prohibited_practices(output)

        assert result.passed
        assert "high" in result.details.lower()

    def test_prohibited_minimal_risk_allowed(self):
        """Test that minimal risk systems pass"""
        output = AgentOutput(
            content="Spam detected",
            metadata={"use_case": "spam_filter"}
        )
        result = check_ai_act_prohibited_practices(output)

        assert result.passed
        assert "minimal" in result.details.lower()


# =============================================================================
# Convenience Functions Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_validate_ai_act_compliance_all_pass(self):
        """Test validate_ai_act_compliance with compliant output"""
        output = AgentOutput(
            content="Spam detected",
            metadata={
                "use_case": "spam_filter",
                "ai_disclosure": True,
                "system_info": "AI spam detection"
            }
        )
        results = validate_ai_act_compliance(output)

        assert len(results) == 3  # 3 checks
        assert all(r.passed for r in results)

    def test_validate_ai_act_compliance_high_risk(self):
        """Test validate_ai_act_compliance with high-risk system"""
        output = AgentOutput(
            content="Loan approved",
            metadata={
                "use_case": "loan_approval",
                "ai_disclosure": True,
                "system_info": "AI credit system",
                "capabilities": "Credit evaluation",
                "limitations": "Recent data may not be considered",
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_in_the_loop",
                "overseer_id": "officer_123",
                "can_override": True
            }
        )
        results = validate_ai_act_compliance(output)

        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_validate_ai_act_compliance_violations(self):
        """Test validate_ai_act_compliance with violations"""
        output = AgentOutput(
            content="Decision",
            metadata={"use_case": "loan", "ai_disclosure": False}
        )
        results = validate_ai_act_compliance(output)

        # Should have some failures
        failures = [r for r in results if not r.passed]
        assert len(failures) > 0

    def test_get_ai_act_guardrails(self):
        """Test getting all AI Act guardrails"""
        guardrails = get_ai_act_guardrails()

        assert len(guardrails) == 3
        assert ARTICLE_5_PROHIBITED_PRACTICES in guardrails
        assert ARTICLE_13_TRANSPARENCY in guardrails
        assert ARTICLE_14_HUMAN_OVERSIGHT in guardrails


# =============================================================================
# Guardrail Integration Tests
# =============================================================================


class TestGuardrails:
    """Tests for pre-configured guardrails"""

    def test_article_13_guardrail_properties(self):
        """Test Article 13 guardrail configuration"""
        assert ARTICLE_13_TRANSPARENCY.name == "EU_AI_Act_Article_13_Transparency"
        assert ARTICLE_13_TRANSPARENCY.severity == "WARNING"

    def test_article_14_guardrail_properties(self):
        """Test Article 14 guardrail configuration"""
        assert ARTICLE_14_HUMAN_OVERSIGHT.name == "EU_AI_Act_Article_14_Human_Oversight"
        assert ARTICLE_14_HUMAN_OVERSIGHT.severity == "BLOCKING"

    def test_article_5_guardrail_properties(self):
        """Test Article 5 guardrail configuration"""
        assert ARTICLE_5_PROHIBITED_PRACTICES.name == "EU_AI_Act_Article_5_Prohibited_Practices"
        assert ARTICLE_5_PROHIBITED_PRACTICES.severity == "BLOCKING"

    def test_article_13_guardrail_check(self):
        """Test Article 13 guardrail check function"""
        output = AgentOutput(
            content="Response",
            metadata={
                "ai_disclosure": True,
                "system_info": "AI assistant",
                "use_case": "chatbot"
            }
        )
        result = ARTICLE_13_TRANSPARENCY.check(output)
        assert result.passed

    def test_article_14_guardrail_check(self):
        """Test Article 14 guardrail check function"""
        output = AgentOutput(
            content="Decision",
            metadata={
                "use_case": "spam_filter",  # Minimal risk
            }
        )
        result = ARTICLE_14_HUMAN_OVERSIGHT.check(output)
        assert result.passed  # Minimal risk doesn't require oversight

    def test_article_5_guardrail_check(self):
        """Test Article 5 guardrail check function"""
        output = AgentOutput(
            content="Score",
            metadata={"use_case": "social_scoring"}
        )
        result = ARTICLE_5_PROHIBITED_PRACTICES.check(output)
        assert not result.passed  # Social scoring is prohibited


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple components"""

    def test_full_high_risk_workflow_compliant(self):
        """Test complete high-risk AI system workflow"""
        output = AgentOutput(
            content="Credit score: 750 - Loan approved",
            metadata={
                "use_case": "credit_score",
                # Article 13 - Transparency
                "ai_disclosure": True,
                "system_info": "AI Credit Scoring System v3.0",
                "capabilities": "Analyzes credit history, income, debt ratios",
                "limitations": "Cannot consider recent life events or contextual factors",
                # Article 14 - Human Oversight
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_in_the_loop",
                "overseer_id": "credit_officer_789",
                "can_override": True,
            }
        )

        # Check risk classification
        risk = classify_ai_system_risk(output.metadata["use_case"])
        assert risk == AISystemRiskLevel.HIGH

        # Check all compliance
        results = validate_ai_act_compliance(output)
        assert all(r.passed for r in results)

    def test_full_prohibited_workflow(self):
        """Test that prohibited practices are blocked"""
        output = AgentOutput(
            content="Social credit score: 850",
            metadata={"use_case": "social_credit"}
        )

        # Should be classified as unacceptable
        risk = classify_ai_system_risk(output.metadata["use_case"])
        assert risk == AISystemRiskLevel.UNACCEPTABLE

        # Should fail prohibited practices check
        results = validate_ai_act_compliance(output)
        prohibited_result = results[0]  # First check is prohibited practices
        assert not prohibited_result.passed

    def test_full_minimal_risk_workflow(self):
        """Test minimal risk AI system with basic compliance"""
        output = AgentOutput(
            content="This email is spam",
            metadata={
                "use_case": "spam_filter",
                "ai_disclosure": True,
                "system_info": "AI spam detection system"
            }
        )

        # Check risk classification
        risk = classify_ai_system_risk(output.metadata["use_case"])
        assert risk == AISystemRiskLevel.MINIMAL

        # Should pass all checks (minimal risk has fewer requirements)
        results = validate_ai_act_compliance(output)
        assert all(r.passed for r in results)
