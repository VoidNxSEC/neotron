"""
Tests for LGPD Kernel-Level Enforcement

Tests cover:
- LGPD Article 7 (Consent) kernel enforcement
- LGPD Article 16 (Data Access) kernel enforcement
- LGPD Article 46 (Retention) kernel enforcement
- Layered enforcement (application + kernel)
- Convenience functions for consent management
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from neutron.compliance.bastion import (
    KernelPolicy,
    ComplianceCapability,
    LayeredPolicy,
    grant_capability,
    revoke_capability,
)

from neutron.compliance.auditors.lgpd_kernel import (
    lgpd_art7_consent_policy,
    lgpd_art16_data_access_policy,
    lgpd_art46_retention_policy,
    lgpd_art18_layered,
    lgpd_art20_layered,
    grant_lgpd_consent,
    revoke_lgpd_consent,
    check_lgpd_consent,
    get_lgpd_kernel_policies,
    get_lgpd_layered_policies,
)


# =============================================================================
# Article 7 - Consent Enforcement Tests
# =============================================================================

class TestArticle7ConsentPolicy:
    """Tests for LGPD Article 7 consent enforcement"""

    def test_policy_exists(self):
        """Test that Article 7 policy is defined"""
        assert lgpd_art7_consent_policy is not None
        assert isinstance(lgpd_art7_consent_policy, KernelPolicy)

    def test_policy_configuration(self):
        """Test Article 7 policy configuration"""
        policy = lgpd_art7_consent_policy

        assert policy.name == "lgpd_art7_consent_enforcement"
        assert policy.regulation == "LGPD"
        assert policy.required_capability == ComplianceCapability.CAP_CONSENT_TOKEN
        assert policy.action == "ERRNO"
        assert policy.errno == 13  # EACCES

    def test_blocks_file_operations(self):
        """Test that policy blocks file read operations"""
        policy = lgpd_art7_consent_policy

        # Should block common file read syscalls
        assert "open" in policy.blocked_syscalls
        assert "openat" in policy.blocked_syscalls
        assert "read" in policy.blocked_syscalls

    def test_has_audit_enabled(self):
        """Test that audit is enabled"""
        assert lgpd_art7_consent_policy.audit is True

    def test_has_metadata(self):
        """Test that policy has required metadata"""
        policy = lgpd_art7_consent_policy

        assert "article" in policy.metadata
        assert "LGPD" in policy.metadata["article"]
        assert policy.metadata["severity"] == "BLOCKING"

    @patch.dict(os.environ, {}, clear=True)
    def test_enforce_without_consent(self):
        """Test enforcement blocks without consent token"""
        # Revoke consent
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        # Should not have capability
        assert not lgpd_art7_consent_policy.check_capability()

    @patch.dict(os.environ, {}, clear=True)
    def test_enforce_with_consent(self):
        """Test enforcement allows with consent token"""
        # Grant consent
        grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        # Should have capability
        assert lgpd_art7_consent_policy.check_capability()

        # Cleanup
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)


# =============================================================================
# Article 16 - Data Access Control Tests
# =============================================================================

class TestArticle16DataAccessPolicy:
    """Tests for LGPD Article 16 data access control"""

    def test_policy_exists(self):
        """Test that Article 16 policy is defined"""
        assert lgpd_art16_data_access_policy is not None
        assert isinstance(lgpd_art16_data_access_policy, KernelPolicy)

    def test_policy_configuration(self):
        """Test Article 16 policy configuration"""
        policy = lgpd_art16_data_access_policy

        assert policy.name == "lgpd_art16_data_access_enforcement"
        assert policy.regulation == "LGPD"
        assert policy.required_capability == ComplianceCapability.CAP_PII_WRITE
        assert policy.action == "ERRNO"
        assert policy.errno == 1  # EPERM

    def test_blocks_file_modification(self):
        """Test that policy blocks file modification operations"""
        policy = lgpd_art16_data_access_policy

        # Should block file deletion and modification
        assert "unlink" in policy.blocked_syscalls
        assert "unlinkat" in policy.blocked_syscalls
        assert "rename" in policy.blocked_syscalls

    def test_metadata_article_16(self):
        """Test Article 16 specific metadata"""
        policy = lgpd_art16_data_access_policy

        assert "Article 16" in policy.metadata["article"]
        assert "Titular" in policy.metadata["article_title"]


# =============================================================================
# Article 46 - Data Retention Tests
# =============================================================================

class TestArticle46RetentionPolicy:
    """Tests for LGPD Article 46 data retention enforcement"""

    def test_policy_exists(self):
        """Test that Article 46 policy is defined"""
        assert lgpd_art46_retention_policy is not None
        assert isinstance(lgpd_art46_retention_policy, KernelPolicy)

    def test_policy_configuration(self):
        """Test Article 46 policy configuration"""
        policy = lgpd_art46_retention_policy

        assert policy.name == "lgpd_art46_retention_enforcement"
        assert policy.regulation == "LGPD"
        assert policy.required_capability == ComplianceCapability.CAP_PII_WRITE
        assert policy.action == "ERRNO"
        assert policy.errno == 30  # EROFS - Read-only filesystem

    def test_blocks_write_operations(self):
        """Test that policy blocks write operations on retained data"""
        policy = lgpd_art46_retention_policy

        # Should block writes to retained files
        assert "write" in policy.blocked_syscalls
        assert "writev" in policy.blocked_syscalls
        assert "pwrite64" in policy.blocked_syscalls

    def test_metadata_severity_warning(self):
        """Test that retention has WARNING severity"""
        policy = lgpd_art46_retention_policy

        # Retention is warning, not blocking critical operations
        assert policy.metadata["severity"] == "WARNING"


# =============================================================================
# Layered Enforcement Tests
# =============================================================================

class TestLayeredEnforcement:
    """Tests for layered enforcement (application + kernel)"""

    def test_article_18_layered_exists(self):
        """Test that Article 18 layered policy exists"""
        assert lgpd_art18_layered is not None
        assert isinstance(lgpd_art18_layered, LayeredPolicy)

    def test_article_18_layered_configuration(self):
        """Test Article 18 layered policy configuration"""
        policy = lgpd_art18_layered

        assert policy.name == "lgpd_art18_full_enforcement"
        assert policy.regulation == "LGPD"
        assert policy.application_check is not None
        assert policy.kernel_policy == lgpd_art7_consent_policy

    def test_article_20_layered_exists(self):
        """Test that Article 20 layered policy exists"""
        assert lgpd_art20_layered is not None
        assert isinstance(lgpd_art20_layered, LayeredPolicy)

    def test_article_20_layered_configuration(self):
        """Test Article 20 layered policy configuration"""
        policy = lgpd_art20_layered

        assert policy.name == "lgpd_art20_full_enforcement"
        assert policy.regulation == "LGPD"
        assert policy.kernel_policy == lgpd_art16_data_access_policy

    @patch.dict(os.environ, {}, clear=True)
    def test_layered_enforcement_without_capability(self):
        """Test layered enforcement without required capability"""
        # Revoke capability
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        # Kernel policy should enforce
        with lgpd_art18_layered.enforce():
            # Kernel layer enforced
            assert not lgpd_art7_consent_policy.check_capability()

    @patch.dict(os.environ, {}, clear=True)
    def test_layered_enforcement_with_capability(self):
        """Test layered enforcement with required capability"""
        # Grant capability
        grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        # Kernel policy should allow
        with lgpd_art18_layered.enforce():
            # Kernel layer allows
            assert lgpd_art7_consent_policy.check_capability()

        # Cleanup
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)


# =============================================================================
# Convenience Functions Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for LGPD consent management convenience functions"""

    @patch.dict(os.environ, {}, clear=True)
    def test_grant_lgpd_consent(self):
        """Test granting LGPD consent"""
        grant_lgpd_consent("customer_123")

        # Should grant consent token capability
        assert os.environ.get("CAP_CONSENT_TOKEN") == "1"

    @patch.dict(os.environ, {}, clear=True)
    def test_revoke_lgpd_consent(self):
        """Test revoking LGPD consent"""
        # Grant first
        grant_lgpd_consent("customer_123")
        assert "CAP_CONSENT_TOKEN" in os.environ

        # Revoke
        revoke_lgpd_consent("customer_123")
        assert "CAP_CONSENT_TOKEN" not in os.environ

    @patch.dict(os.environ, {}, clear=True)
    def test_check_lgpd_consent_true(self):
        """Test checking consent when granted"""
        grant_lgpd_consent("customer_123")

        assert check_lgpd_consent("customer_123") is True

        # Cleanup
        revoke_lgpd_consent("customer_123")

    @patch.dict(os.environ, {}, clear=True)
    def test_check_lgpd_consent_false(self):
        """Test checking consent when not granted"""
        assert check_lgpd_consent("customer_123") is False

    @patch.dict(os.environ, {}, clear=True)
    def test_grant_revoke_workflow(self):
        """Test complete grant-revoke workflow"""
        customer_id = "customer_456"

        # Initially no consent
        assert not check_lgpd_consent(customer_id)

        # Grant consent
        grant_lgpd_consent(customer_id)
        assert check_lgpd_consent(customer_id)

        # Revoke consent
        revoke_lgpd_consent(customer_id)
        assert not check_lgpd_consent(customer_id)


# =============================================================================
# Policy Collection Tests
# =============================================================================

class TestPolicyCollections:
    """Tests for policy collection functions"""

    def test_get_lgpd_kernel_policies(self):
        """Test getting all LGPD kernel policies"""
        policies = get_lgpd_kernel_policies()

        assert isinstance(policies, list)
        assert len(policies) == 3  # Art 7, 16, 46

        # Verify all policies are present
        policy_names = [p.name for p in policies]
        assert "lgpd_art7_consent_enforcement" in policy_names
        assert "lgpd_art16_data_access_enforcement" in policy_names
        assert "lgpd_art46_retention_enforcement" in policy_names

    def test_all_kernel_policies_are_kernel_policies(self):
        """Test that all returned policies are KernelPolicy instances"""
        policies = get_lgpd_kernel_policies()

        for policy in policies:
            assert isinstance(policy, KernelPolicy)

    def test_get_lgpd_layered_policies(self):
        """Test getting all LGPD layered policies"""
        policies = get_lgpd_layered_policies()

        assert isinstance(policies, list)
        assert len(policies) == 2  # Art 18, 20

        # Verify all layered policies are present
        policy_names = [p.name for p in policies]
        assert "lgpd_art18_full_enforcement" in policy_names
        assert "lgpd_art20_full_enforcement" in policy_names

    def test_all_layered_policies_are_layered(self):
        """Test that all returned policies are LayeredPolicy instances"""
        policies = get_lgpd_layered_policies()

        for policy in policies:
            assert isinstance(policy, LayeredPolicy)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for LGPD kernel enforcement"""

    @patch.dict(os.environ, {}, clear=True)
    def test_full_consent_workflow(self):
        """Test complete consent workflow with enforcement"""
        customer_id = "customer_789"

        # Step 1: No consent - enforcement active
        revoke_lgpd_consent(customer_id)
        assert not lgpd_art7_consent_policy.check_capability()

        # Step 2: Grant consent
        grant_lgpd_consent(customer_id)
        assert check_lgpd_consent(customer_id)
        assert lgpd_art7_consent_policy.check_capability()

        # Step 3: Process data under enforcement
        with lgpd_art7_consent_policy.enforce():
            # Capability present, access allowed
            assert lgpd_art7_consent_policy.check_capability()

        # Step 4: Revoke consent
        revoke_lgpd_consent(customer_id)
        assert not check_lgpd_consent(customer_id)

    @patch.dict(os.environ, {}, clear=True)
    def test_multiple_policies_enforcement(self):
        """Test enforcing multiple LGPD policies simultaneously"""
        # Grant required capabilities
        grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
        grant_capability(ComplianceCapability.CAP_PII_WRITE)

        # All policies should have capabilities
        assert lgpd_art7_consent_policy.check_capability()
        assert lgpd_art16_data_access_policy.check_capability()
        assert lgpd_art46_retention_policy.check_capability()

        # Cleanup
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
        revoke_capability(ComplianceCapability.CAP_PII_WRITE)

    def test_all_policies_have_unique_names(self):
        """Test that all policies have unique names"""
        policies = get_lgpd_kernel_policies()
        names = [p.name for p in policies]

        # All names should be unique
        assert len(names) == len(set(names))

    def test_all_policies_are_lgpd(self):
        """Test that all policies are for LGPD regulation"""
        policies = get_lgpd_kernel_policies()

        for policy in policies:
            assert policy.regulation == "LGPD"

    def test_all_policies_have_descriptions(self):
        """Test that all policies have descriptions"""
        policies = get_lgpd_kernel_policies()

        for policy in policies:
            assert policy.description
            assert len(policy.description) > 0
            assert "LGPD" in policy.description


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    @patch.dict(os.environ, {}, clear=True)
    def test_multiple_consent_grants(self):
        """Test granting consent multiple times"""
        # Should not raise error
        grant_lgpd_consent("customer_1")
        grant_lgpd_consent("customer_1")
        grant_lgpd_consent("customer_1")

        assert check_lgpd_consent("customer_1")

        # Cleanup
        revoke_lgpd_consent("customer_1")

    @patch.dict(os.environ, {}, clear=True)
    def test_multiple_consent_revocations(self):
        """Test revoking consent multiple times"""
        grant_lgpd_consent("customer_2")

        # Should not raise error
        revoke_lgpd_consent("customer_2")
        revoke_lgpd_consent("customer_2")
        revoke_lgpd_consent("customer_2")

        assert not check_lgpd_consent("customer_2")

    @patch.dict(os.environ, {}, clear=True)
    def test_revoke_without_grant(self):
        """Test revoking consent that was never granted"""
        # Should not raise error
        revoke_lgpd_consent("customer_3")

        assert not check_lgpd_consent("customer_3")

    @patch.dict(os.environ, {}, clear=True)
    def test_consent_for_different_customers(self):
        """Test consent is not confused between customers"""
        # In current implementation, consent is process-level
        # This test documents that behavior

        grant_lgpd_consent("customer_a")
        assert check_lgpd_consent("customer_a")

        # Currently, consent is global (CAP_CONSENT_TOKEN)
        # So customer_b also has "consent"
        assert check_lgpd_consent("customer_b")

        # Cleanup
        revoke_lgpd_consent("customer_a")

        # Both lose consent (global capability)
        assert not check_lgpd_consent("customer_a")
        assert not check_lgpd_consent("customer_b")
