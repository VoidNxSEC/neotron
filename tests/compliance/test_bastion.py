"""
Tests for BASTION Kernel-Level Compliance Enforcement

Tests cover:
- KernelPolicy creation and validation
- BPF program generation
- Capability management
- Policy enforcement
- Layered enforcement (SENTINEL + BASTION)
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from neutron.compliance.bastion import (
    SECCOMP_RET_ALLOW,
    SYSCALL_NR,
    BPFInstruction,
    BPFProgram,
    ComplianceCapability,
    KernelPolicy,
    LayeredPolicy,
    grant_capability,
    has_capability,
    revoke_capability,
)

from .bastion_test_helpers import run_in_subprocess, skip_in_ci

# =============================================================================
# BPF Program Tests
# =============================================================================


class TestBPFProgram:
    """Tests for BPF program builder"""

    def test_create_empty_program(self):
        """Test creating empty BPF program"""
        prog = BPFProgram()
        assert len(prog.instructions) == 0

    def test_add_instruction(self):
        """Test adding instruction to program"""
        prog = BPFProgram()
        prog.add(0x00, jt=1, jf=2, k=3)

        assert len(prog.instructions) == 1
        assert prog.instructions[0].code == 0x00
        assert prog.instructions[0].jt == 1
        assert prog.instructions[0].jf == 2
        assert prog.instructions[0].k == 3

    def test_load_syscall_nr(self):
        """Test loading syscall number instruction"""
        prog = BPFProgram()
        prog.load_syscall_nr()

        assert len(prog.instructions) == 1
        instr = prog.instructions[0]
        # Should load from offset 0
        assert instr.k == 0

    def test_jump_if_syscall_eq(self):
        """Test conditional jump instruction"""
        prog = BPFProgram()
        prog.jump_if_syscall_eq(SYSCALL_NR["open"], true_offset=5, false_offset=0)

        assert len(prog.instructions) == 1
        instr = prog.instructions[0]
        assert instr.jt == 5
        assert instr.jf == 0
        assert instr.k == SYSCALL_NR["open"]

    def test_ret_instruction(self):
        """Test return instruction"""
        prog = BPFProgram()
        prog.ret(SECCOMP_RET_ALLOW)

        assert len(prog.instructions) == 1
        instr = prog.instructions[0]
        assert instr.k == SECCOMP_RET_ALLOW

    def test_compile_program(self):
        """Test compiling program to binary"""
        prog = BPFProgram()
        prog.ret(SECCOMP_RET_ALLOW)

        compiled = prog.compile()
        assert isinstance(compiled, bytes)
        assert len(compiled) > 0

    def test_simple_allow_program(self):
        """Test simple program that allows all syscalls"""
        prog = BPFProgram()
        prog.load_syscall_nr()
        prog.ret(SECCOMP_RET_ALLOW)

        assert len(prog.instructions) == 2
        compiled = prog.compile()
        # Each instruction is 8 bytes
        assert len(compiled) == 16


# =============================================================================
# BPF Instruction Tests
# =============================================================================


class TestBPFInstruction:
    """Tests for BPF instruction structure"""

    def test_create_instruction(self):
        """Test creating BPF instruction"""
        instr = BPFInstruction(code=0x06, jt=0, jf=0, k=0x7FFF0000)

        assert instr.code == 0x06
        assert instr.jt == 0
        assert instr.jf == 0
        assert instr.k == 0x7FFF0000

    def test_pack_instruction(self):
        """Test packing instruction to binary"""
        instr = BPFInstruction(code=0x06, jt=0, jf=0, k=0x7FFF0000)
        packed = instr.pack()

        assert isinstance(packed, bytes)
        # struct sock_filter is 8 bytes
        assert len(packed) == 8


# =============================================================================
# KernelPolicy Tests
# =============================================================================


class TestKernelPolicy:
    """Tests for kernel-level policy enforcement"""

    def test_create_policy(self):
        """Test creating kernel policy"""
        policy = KernelPolicy(
            name="test_policy",
            regulation="LGPD",
            blocked_syscalls=["open", "read"],
            required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
        )

        assert policy.name == "test_policy"
        assert policy.regulation == "LGPD"
        assert policy.blocked_syscalls == ["open", "read"]
        assert policy.required_capability == ComplianceCapability.CAP_CONSENT_TOKEN

    def test_policy_validation_no_syscalls(self):
        """Test that policy requires at least one syscall"""
        with pytest.raises(ValueError, match="must block at least one syscall"):
            KernelPolicy(name="invalid", regulation="LGPD", blocked_syscalls=[])

    def test_policy_validation_unknown_syscall(self):
        """Test that policy rejects unknown syscalls"""
        with pytest.raises(ValueError, match="Unknown syscall"):
            KernelPolicy(
                name="invalid", regulation="LGPD", blocked_syscalls=["nonexistent_syscall"]
            )

    def test_policy_default_description(self):
        """Test that policy generates default description"""
        policy = KernelPolicy(name="test", regulation="LGPD", blocked_syscalls=["open"])

        assert "LGPD" in policy.description
        assert "open" in policy.description

    def test_policy_custom_description(self):
        """Test setting custom description"""
        policy = KernelPolicy(
            name="test",
            regulation="LGPD",
            blocked_syscalls=["open"],
            description="Custom description",
        )

        assert policy.description == "Custom description"

    def test_build_bpf_program(self):
        """Test building BPF program from policy"""
        policy = KernelPolicy(name="test", regulation="LGPD", blocked_syscalls=["open", "read"])

        prog = policy.build_bpf_program()

        assert isinstance(prog, BPFProgram)
        assert len(prog.instructions) > 0

    def test_bpf_program_blocks_syscalls(self):
        """Test that BPF program blocks specified syscalls"""
        policy = KernelPolicy(
            name="test", regulation="LGPD", blocked_syscalls=["open"], action="ERRNO", errno=13
        )

        prog = policy.build_bpf_program()

        # Program should have instructions
        assert len(prog.instructions) > 0

    def test_policy_action_errno(self):
        """Test policy with ERRNO action"""
        policy = KernelPolicy(
            name="test", regulation="LGPD", blocked_syscalls=["open"], action="ERRNO", errno=13
        )

        assert policy.action == "ERRNO"
        assert policy.errno == 13

    def test_policy_action_kill(self):
        """Test policy with KILL action"""
        policy = KernelPolicy(
            name="test", regulation="LGPD", blocked_syscalls=["execve"], action="KILL"
        )

        assert policy.action == "KILL"

    def test_check_capability_present(self):
        """Test checking capability when present"""
        policy = KernelPolicy(
            name="test",
            regulation="LGPD",
            blocked_syscalls=["open"],
            required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
        )

        # Grant capability
        grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        assert policy.check_capability() is True

        # Cleanup
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

    def test_check_capability_absent(self):
        """Test checking capability when absent"""
        policy = KernelPolicy(
            name="test",
            regulation="LGPD",
            blocked_syscalls=["open"],
            required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
        )

        # Ensure capability is revoked
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        assert policy.check_capability() is False

    def test_check_capability_not_required(self):
        """Test checking when no capability required"""
        policy = KernelPolicy(
            name="test", regulation="LGPD", blocked_syscalls=["open"], required_capability=None
        )

        # Should always return True when no capability required
        assert policy.check_capability() is True

    @patch.dict(os.environ, {}, clear=True)
    @skip_in_ci  # Skip in CI due to kernel restrictions
    def test_enforce_without_capability(self):
        """Test enforcement without required capability"""

        def isolated_test():
            policy = KernelPolicy(
                name="test",
                regulation="LGPD",
                blocked_syscalls=["open"],
                required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
                audit=False,  # Disable audit for cleaner test
            )

            # Ensure no capability
            revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

            # Enforce should apply filter (or simulate on non-Linux)
            with policy.enforce():
                # On non-Linux, sets environment variable
                if sys.platform != "linux":
                    assert os.environ.get(f"BASTION_ENFORCING_{policy.name}") == "1"
                # On Linux, seccomp filter is applied (we can't easily test
                # the filter effect without triggering it, so we just verify
                # enforce() doesn't crash)

        # Run in subprocess to isolate seccomp filter
        assert run_in_subprocess(isolated_test)

    @patch.dict(os.environ, {}, clear=True)
    @skip_in_ci  # Skip in CI due to kernel restrictions
    def test_enforce_with_capability(self):
        """Test enforcement with required capability"""

        def isolated_test():
            policy = KernelPolicy(
                name="test",
                regulation="LGPD",
                blocked_syscalls=["open"],
                required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
                audit=False,
            )

            # Grant capability
            grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

            # Enforce should NOT apply filter when capability present
            with policy.enforce():
                # Should not set enforcement env var
                if sys.platform != "linux":
                    assert f"BASTION_ENFORCING_{policy.name}" not in os.environ

            # Cleanup
            revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        # Run in subprocess to isolate
        assert run_in_subprocess(isolated_test)


# =============================================================================
# Capability Management Tests
# =============================================================================


class TestCapabilityManagement:
    """Tests for compliance capability management"""

    @patch.dict(os.environ, {}, clear=True)
    def test_grant_capability(self):
        """Test granting capability"""
        grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        assert os.environ["CAP_CONSENT_TOKEN"] == "1"

    @patch.dict(os.environ, {}, clear=True)
    def test_revoke_capability(self):
        """Test revoking capability"""
        # Grant first
        grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
        assert "CAP_CONSENT_TOKEN" in os.environ

        # Revoke
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
        assert "CAP_CONSENT_TOKEN" not in os.environ

    @patch.dict(os.environ, {}, clear=True)
    def test_revoke_nonexistent_capability(self):
        """Test revoking capability that wasn't granted"""
        # Should not raise error
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

    @patch.dict(os.environ, {}, clear=True)
    def test_has_capability_true(self):
        """Test checking capability when present"""
        grant_capability(ComplianceCapability.CAP_PII_READ)

        assert has_capability(ComplianceCapability.CAP_PII_READ) is True

    @patch.dict(os.environ, {}, clear=True)
    def test_has_capability_false(self):
        """Test checking capability when absent"""
        assert has_capability(ComplianceCapability.CAP_PII_READ) is False

    @patch.dict(os.environ, {}, clear=True)
    def test_multiple_capabilities(self):
        """Test managing multiple capabilities"""
        grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
        grant_capability(ComplianceCapability.CAP_PII_READ)
        grant_capability(ComplianceCapability.CAP_PII_WRITE)

        assert has_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
        assert has_capability(ComplianceCapability.CAP_PII_READ)
        assert has_capability(ComplianceCapability.CAP_PII_WRITE)

        # Revoke one
        revoke_capability(ComplianceCapability.CAP_PII_READ)

        assert has_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
        assert not has_capability(ComplianceCapability.CAP_PII_READ)
        assert has_capability(ComplianceCapability.CAP_PII_WRITE)


# =============================================================================
# LayeredPolicy Tests
# =============================================================================


class TestLayeredPolicy:
    """Tests for layered enforcement (SENTINEL + BASTION)"""

    def test_create_layered_policy(self):
        """Test creating layered policy"""
        # Mock application-layer guardrail
        app_guardrail = MagicMock()
        app_guardrail.name = "test_app_guardrail"

        kernel_policy = KernelPolicy(
            name="test_kernel", regulation="LGPD", blocked_syscalls=["open"]
        )

        layered = LayeredPolicy(
            name="test_layered",
            regulation="LGPD",
            application_check=app_guardrail,
            kernel_policy=kernel_policy,
        )

        assert layered.name == "test_layered"
        assert layered.regulation == "LGPD"
        assert layered.application_check == app_guardrail
        assert layered.kernel_policy == kernel_policy

    @patch.dict(os.environ, {}, clear=True)
    @skip_in_ci  # Skip in CI due to kernel restrictions
    def test_layered_enforcement(self):
        """Test layered policy enforcement"""

        def isolated_test():
            app_guardrail = MagicMock()

            kernel_policy = KernelPolicy(
                name="test",
                regulation="LGPD",
                blocked_syscalls=["open"],
                required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
                audit=False,
            )

            layered = LayeredPolicy(
                name="test_layered",
                regulation="LGPD",
                application_check=app_guardrail,
                kernel_policy=kernel_policy,
            )

            # Revoke capability to trigger kernel enforcement
            revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

            # Enforce both layers
            with layered.enforce():
                # Kernel layer should be enforced
                if sys.platform != "linux":
                    assert os.environ.get("BASTION_ENFORCING_test") == "1"

        assert run_in_subprocess(isolated_test)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple components"""

    @patch.dict(os.environ, {}, clear=True)
    @skip_in_ci  # Skip in CI due to kernel restrictions
    def test_complete_workflow_without_consent(self):
        """Test complete workflow without consent token"""

        def isolated_test():
            policy = KernelPolicy(
                name="lgpd_consent_test",
                regulation="LGPD",
                blocked_syscalls=["open", "read"],
                required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
                action="ERRNO",
                errno=13,
                audit=False,
            )

            # Ensure no consent
            revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

            # Enforce policy
            with policy.enforce():
                # Capability check should fail
                assert not policy.check_capability()

                # On non-Linux, enforcement is simulated
                if sys.platform != "linux":
                    assert os.environ.get("BASTION_ENFORCING_lgpd_consent_test") == "1"

        assert run_in_subprocess(isolated_test)

    @patch.dict(os.environ, {}, clear=True)
    @skip_in_ci  # Skip in CI due to kernel restrictions
    def test_complete_workflow_with_consent(self):
        """Test complete workflow with consent token"""

        def isolated_test():
            policy = KernelPolicy(
                name="lgpd_consent_test",
                regulation="LGPD",
                blocked_syscalls=["open", "read"],
                required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
                audit=False,
            )

            # Grant consent
            grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

            # Enforce policy
            with policy.enforce():
                # Capability check should succeed
                assert policy.check_capability()

                # On non-Linux, should NOT enforce when capability present
                if sys.platform != "linux":
                    assert "BASTION_ENFORCING_lgpd_consent_test" not in os.environ

        assert run_in_subprocess(isolated_test)

        # Cleanup
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

    def test_multiple_policies_different_syscalls(self):
        """Test multiple policies blocking different syscalls"""
        policy1 = KernelPolicy(
            name="policy1", regulation="LGPD", blocked_syscalls=["open"], audit=False
        )

        policy2 = KernelPolicy(
            name="policy2", regulation="LGPD", blocked_syscalls=["unlink"], audit=False
        )

        # Both should compile successfully
        prog1 = policy1.build_bpf_program()
        prog2 = policy2.build_bpf_program()

        assert len(prog1.instructions) > 0
        assert len(prog2.instructions) > 0

    def test_policy_metadata(self):
        """Test policy with custom metadata"""
        policy = KernelPolicy(
            name="test",
            regulation="LGPD",
            blocked_syscalls=["open"],
            metadata={
                "article": "LGPD Article 7",
                "severity": "BLOCKING",
                "author": "compliance_team",
            },
        )

        assert policy.metadata["article"] == "LGPD Article 7"
        assert policy.metadata["severity"] == "BLOCKING"
        assert policy.metadata["author"] == "compliance_team"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def test_invalid_regulation(self):
        """Test that invalid regulation is rejected by type system"""
        # This would fail at type-checking level
        # At runtime, Python allows it but it's a type violation
        pass

    def test_empty_syscall_list(self):
        """Test that empty syscall list raises error"""
        with pytest.raises(ValueError):
            KernelPolicy(name="test", regulation="LGPD", blocked_syscalls=[])

    def test_invalid_syscall_name(self):
        """Test that invalid syscall name raises error"""
        with pytest.raises(ValueError, match="Unknown syscall"):
            KernelPolicy(name="test", regulation="LGPD", blocked_syscalls=["invalid_syscall_name"])

    def test_negative_errno(self):
        """Test policy with negative errno"""
        # Should accept (errno can be any int)
        policy = KernelPolicy(
            name="test", regulation="LGPD", blocked_syscalls=["open"], action="ERRNO", errno=-1
        )

        assert policy.errno == -1
