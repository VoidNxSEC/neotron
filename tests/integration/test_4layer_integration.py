"""
Integration tests for 4-layer NEXUS compliance flow.
"""

from unittest.mock import patch

import pytest

from neutron.compliance.nexus_flow import (
    ComplianceDecision,
    ComplianceRequest,
    LayerResult,
    NEXUSComplianceFlow,
)


@pytest.mark.asyncio
async def test_flow_approved_with_consent():
    """Test that a request with valid consent is approved."""
    flow = NEXUSComplianceFlow(
        enable_bastion=False,  # Disable for testing
        enable_smart_contracts=False,
        enable_memory=False,
    )

    request = ComplianceRequest(
        customer_id="test_customer",
        action="test_action",
        data={"test": "data"},
        consent_token="lgpd_consent_test123",
        regulation="LGPD",
    )

    # Mock the CORTEX layer to return approved
    with patch.object(flow, "_layer3_cortex_oracle") as mock_cortex:
        mock_cortex.return_value = (
            LayerResult(
                layer_name="CORTEX",
                passed=True,
                status="APPROVED",
                details="Mocked approval",
                processing_time_ms=100.0,
                metadata={"consensus_confidence": 0.9},
            ),
            "Mocked explanation",
        )

        response = await flow.validate(request)

        # Should pass all layers
        assert "SENTINEL" in response.layers
        assert response.layers["SENTINEL"].passed is True

        assert "CORTEX" in response.layers
        assert response.layers["CORTEX"].passed is True

        # Final decision should be approved
        assert response.decision in [
            ComplianceDecision.APPROVED,
            ComplianceDecision.CONDITIONAL,
        ]


@pytest.mark.asyncio
async def test_flow_rejected_no_consent():
    """Test that a request without consent is rejected at Layer 1."""
    flow = NEXUSComplianceFlow()

    request = ComplianceRequest(
        customer_id="test_customer",
        action="test_action",
        data={"test": "data"},
        consent_token=None,  # No consent!
        regulation="LGPD",
    )

    response = await flow.validate(request)

    # Should be rejected at SENTINEL
    assert "SENTINEL" in response.layers
    assert response.layers["SENTINEL"].passed is False

    # Should not reach CORTEX
    assert "CORTEX" not in response.layers

    # Final decision should be rejected
    assert response.decision == ComplianceDecision.REJECTED


@pytest.mark.asyncio
async def test_layer1_sentinel():
    """Test Layer 1 (SENTINEL) independently."""
    flow = NEXUSComplianceFlow()

    # Valid request
    request = ComplianceRequest(
        customer_id="test",
        action="test",
        consent_token="lgpd_consent_valid",
    )

    result = await flow._layer1_sentinel(request)

    assert result.layer_name == "SENTINEL"
    assert result.passed is True
    assert result.status == "PASS"

    # Invalid request (no consent)
    request_no_consent = ComplianceRequest(
        customer_id="test",
        action="test",
        consent_token=None,
    )

    result = await flow._layer1_sentinel(request_no_consent)

    assert result.passed is False
    assert "consent" in result.details.lower()


@pytest.mark.asyncio
async def test_layer2_bastion_disabled():
    """Test Layer 2 (BASTION) when disabled."""
    flow = NEXUSComplianceFlow(enable_bastion=False)

    request = ComplianceRequest(
        customer_id="test",
        action="test",
        consent_token="lgpd_consent_test",
    )

    result = await flow._layer2_bastion(request)

    assert result.layer_name == "BASTION"
    assert result.status == "SKIPPED"
    assert result.passed is True


@pytest.mark.asyncio
async def test_layer4_audit():
    """Test Layer 4 (AUDIT) creates audit log."""
    flow = NEXUSComplianceFlow()

    request = ComplianceRequest(
        customer_id="test",
        action="test",
        consent_token="lgpd_consent_test",
    )

    layers = {
        "SENTINEL": LayerResult(
            layer_name="SENTINEL",
            passed=True,
            status="PASS",
            details="Test",
            processing_time_ms=10.0,
        )
    }

    result = await flow._layer4_audit(
        request, ComplianceDecision.APPROVED, layers, "Test explanation"
    )

    assert result.layer_name == "AUDIT"
    assert result.passed is True
    assert result.status == "LOGGED"
    assert "ipfs_cid" in result.metadata or "simulated" in result.details.lower()


@pytest.mark.asyncio
async def test_response_includes_audit_hash():
    """Test that successful validation includes audit hash."""
    flow = NEXUSComplianceFlow(enable_bastion=False)

    request = ComplianceRequest(
        customer_id="test",
        action="test",
        data={"test": "data"},
        consent_token="lgpd_consent_test",
    )

    # Mock CORTEX to return approved
    with patch.object(flow, "_layer3_cortex_oracle") as mock_cortex:
        mock_cortex.return_value = (
            LayerResult(
                layer_name="CORTEX",
                passed=True,
                status="APPROVED",
                details="Approved",
                processing_time_ms=100.0,
                metadata={"consensus_confidence": 0.9},
            ),
            "Test explanation",
        )

        response = await flow.validate(request)

        # Should have audit hash
        assert response.audit_hash is not None
        assert len(response.audit_hash) > 0


@pytest.mark.asyncio
async def test_response_includes_all_layers():
    """Test that response includes results from all executed layers."""
    flow = NEXUSComplianceFlow(enable_bastion=False)

    request = ComplianceRequest(
        customer_id="test",
        action="test",
        consent_token="lgpd_consent_test",
    )

    # Mock CORTEX
    with patch.object(flow, "_layer3_cortex_oracle") as mock_cortex:
        mock_cortex.return_value = (
            LayerResult(
                layer_name="CORTEX",
                passed=True,
                status="APPROVED",
                details="Approved",
                processing_time_ms=100.0,
                metadata={"consensus_confidence": 0.9},
            ),
            "Explanation",
        )

        response = await flow.validate(request)

        # Should have SENTINEL, BASTION (skipped), CORTEX, AUDIT
        assert "SENTINEL" in response.layers
        assert "BASTION" in response.layers
        assert "CORTEX" in response.layers
        assert "AUDIT" in response.layers


def test_compliance_request_defaults():
    """Test ComplianceRequest default values."""
    request = ComplianceRequest(
        customer_id="test",
        action="test",
    )

    assert request.regulation == "LGPD"
    assert request.data == {}
    assert request.metadata == {}
    assert request.request_id is not None
    assert len(request.request_id) > 0
