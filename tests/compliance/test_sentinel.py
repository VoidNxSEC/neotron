"""
Tests for SENTINEL core engine
"""

from datetime import datetime

import pytest

from neutron.compliance.sentinel import (
    AgentOutput,
    ComplianceGuardrail,
    ComplianceViolation,
    EnforcedOutput,
    ValidationResult,
    create_guardrail,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_output():
    """Sample agent output for testing"""
    return AgentOutput(
        content="Test output content",
        metadata={"source": "test"},
        has_explanation=True,
        explanation="This is a test explanation",
        explanation_quality=0.85,
        model_name="test-model",
    )


@pytest.fixture
def passing_check():
    """Check function that always passes"""

    def check(output: AgentOutput) -> ValidationResult:
        return ValidationResult(passed=True, details="Check passed", confidence=1.0)

    return check


@pytest.fixture
def failing_check():
    """Check function that always fails"""

    def check(output: AgentOutput) -> ValidationResult:
        return ValidationResult(passed=False, details="Check failed", confidence=1.0)

    return check


# =============================================================================
# Tests for Data Models
# =============================================================================


def test_validation_result_creation():
    """Test creating a ValidationResult"""
    result = ValidationResult(passed=True, details="Test passed", confidence=0.95)
    assert result.passed is True
    assert result.details == "Test passed"
    assert result.confidence == 0.95


def test_agent_output_creation():
    """Test creating an AgentOutput"""
    output = AgentOutput(
        content="Test content", has_explanation=True, explanation="Test explanation"
    )
    assert output.content == "Test content"
    assert output.has_explanation is True
    assert isinstance(output.timestamp, datetime)


def test_agent_output_without_explanation():
    """Test agent output without explanation"""
    output = AgentOutput(content="Test")
    assert output.has_explanation is False
    assert output.explanation is None
    assert output.explanation_quality == 0.0


# =============================================================================
# Tests for ComplianceGuardrail
# =============================================================================


def test_guardrail_creation(passing_check):
    """Test creating a compliance guardrail"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail", regulation="LGPD", check=passing_check, severity="block"
    )
    assert guardrail.name == "test_guardrail"
    assert guardrail.regulation == "LGPD"
    assert guardrail.severity == "block"
    assert guardrail.enabled is True


def test_guardrail_enforce_passing(passing_check, sample_output):
    """Test guardrail enforcement with passing check"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail", regulation="LGPD", check=passing_check, severity="block"
    )

    enforced = guardrail.enforce(sample_output)

    assert isinstance(enforced, EnforcedOutput)
    assert enforced.validation_result.passed is True
    assert enforced.guardrail_name == "test_guardrail"
    assert enforced.regulation == "LGPD"
    assert enforced.enforced is True


def test_guardrail_enforce_failing_block(failing_check, sample_output):
    """Test guardrail enforcement with failing check and block severity"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail", regulation="LGPD", check=failing_check, severity="block"
    )

    with pytest.raises(ComplianceViolation) as exc_info:
        guardrail.enforce(sample_output)

    violation = exc_info.value
    assert violation.guardrail.name == "test_guardrail"
    assert violation.result.passed is False


def test_guardrail_enforce_failing_warn(failing_check, sample_output):
    """Test guardrail enforcement with failing check and warn severity"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail", regulation="LGPD", check=failing_check, severity="warn"
    )

    # Should not raise exception, just log warning
    enforced = guardrail.enforce(sample_output)

    assert enforced.validation_result.passed is False
    assert enforced.enforced is True


def test_guardrail_enforce_failing_audit(failing_check, sample_output):
    """Test guardrail enforcement with failing check and audit severity"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail", regulation="LGPD", check=failing_check, severity="audit"
    )

    # Should not raise exception, just log for audit
    enforced = guardrail.enforce(sample_output)

    assert enforced.validation_result.passed is False
    assert enforced.enforced is True


def test_guardrail_disabled(failing_check, sample_output):
    """Test that disabled guardrails pass through"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail",
        regulation="LGPD",
        check=failing_check,
        severity="block",
        enabled=False,
    )

    enforced = guardrail.enforce(sample_output)

    assert enforced.validation_result.passed is True
    assert enforced.enforced is False
    assert "disabled" in enforced.validation_result.details


def test_guardrail_enable_disable(passing_check):
    """Test enabling and disabling guardrails"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail", regulation="LGPD", check=passing_check, severity="block"
    )

    assert guardrail.enabled is True

    guardrail.disable()
    assert guardrail.enabled is False

    guardrail.enable()
    assert guardrail.enabled is True


def test_output_hashing(passing_check, sample_output):
    """Test that output hashing is consistent"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail", regulation="LGPD", check=passing_check, severity="block"
    )

    hash1 = guardrail._hash_output(sample_output)
    hash2 = guardrail._hash_output(sample_output)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces 64 hex characters


def test_output_hashing_changes_with_content(passing_check):
    """Test that different content produces different hashes"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail", regulation="LGPD", check=passing_check, severity="block"
    )

    output1 = AgentOutput(content="Content 1")
    output2 = AgentOutput(content="Content 2")

    hash1 = guardrail._hash_output(output1)
    hash2 = guardrail._hash_output(output2)

    assert hash1 != hash2


# =============================================================================
# Tests for Convenience Functions
# =============================================================================


def test_create_guardrail_convenience(passing_check):
    """Test create_guardrail convenience function"""
    guardrail = create_guardrail(
        name="test_guardrail",
        regulation="LGPD",
        check_function=passing_check,
        severity="warn",
        description="Test description",
    )

    assert isinstance(guardrail, ComplianceGuardrail)
    assert guardrail.name == "test_guardrail"
    assert guardrail.severity == "warn"
    assert guardrail.description == "Test description"


# =============================================================================
# Tests for ComplianceViolation Exception
# =============================================================================


def test_compliance_violation_exception(failing_check, sample_output):
    """Test ComplianceViolation exception details"""
    guardrail = ComplianceGuardrail(
        name="test_guardrail", regulation="LGPD", check=failing_check, severity="block"
    )

    try:
        guardrail.enforce(sample_output)
    except ComplianceViolation as e:
        assert e.guardrail.name == "test_guardrail"
        assert e.result.passed is False
        assert e.output == sample_output
        assert "LGPD" in str(e)
        assert "test_guardrail" in str(e)
    else:
        pytest.fail("Expected ComplianceViolation to be raised")


# =============================================================================
# Integration Tests
# =============================================================================


def test_full_workflow_passing():
    """Test full workflow with passing guardrail"""

    def check_has_content(output: AgentOutput) -> ValidationResult:
        if output.content:
            return ValidationResult(True, "Content present")
        return ValidationResult(False, "No content")

    guardrail = ComplianceGuardrail(
        name="content_check", regulation="LGPD", check=check_has_content, severity="block"
    )

    output = AgentOutput(content="Valid content")
    enforced = guardrail.enforce(output)

    assert enforced.validation_result.passed is True


def test_full_workflow_failing():
    """Test full workflow with failing guardrail"""

    def check_has_content(output: AgentOutput) -> ValidationResult:
        if output.content:
            return ValidationResult(True, "Content present")
        return ValidationResult(False, "No content")

    guardrail = ComplianceGuardrail(
        name="content_check", regulation="LGPD", check=check_has_content, severity="block"
    )

    output = AgentOutput(content="")

    with pytest.raises(ComplianceViolation):
        guardrail.enforce(output)
