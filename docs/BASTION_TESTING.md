# BASTION Testing Guide

**Last Updated**: 2026-02-15

## Overview

BASTION provides kernel-level compliance enforcement via seccomp-BPF. Testing this functionality requires special handling due to the **permanent nature** of seccomp filters.

## The seccomp-BPF Challenge

### Why Testing is Tricky

Once a seccomp-BPF filter is applied to a process:
- ✅ It **immediately** blocks specified syscalls
- ⚠️ It is **permanent** for that process
- ⚠️ It **cannot** be removed or modified
- ⚠️ Child processes **inherit** the filter
- ⚠️ Multiple filters can cause conflicts

This causes problems in test suites where:
1. Test A applies filter blocking `open`
2. Test B tries to apply different filter
3. Filters conflict → **segfault** or unexpected blocks
4. All subsequent tests inherit filters → **cascading failures**

### The Solution: Subprocess Isolation

Each BASTION enforcement test runs in an **isolated subprocess**:

```python
def test_bastion_enforcement():
    def isolated_test():
        policy = KernelPolicy(...)
        with policy.enforce():
            # Test code here
            assert something

    # Run in subprocess - filter dies with subprocess
    assert run_in_subprocess(isolated_test)
```

When the subprocess exits, the seccomp filter **dies with it**, preventing:
- Filter conflicts between tests
- Cascading test failures
- CI segfaults

## Test Helpers

### `run_in_subprocess(test_func)`

Runs a test function in an isolated subprocess on Linux. On non-Linux platforms (macOS, Windows), runs directly since enforcement is simulated.

**Usage**:
```python
from tests.compliance.bastion_test_helpers import run_in_subprocess

def test_kernel_enforcement():
    def isolated_test():
        policy = KernelPolicy(
            name="test",
            regulation="LGPD",
            blocked_syscalls=["open"],
        )

        # This seccomp filter is isolated to subprocess
        with policy.enforce():
            # Test kernel enforcement
            pass

    # Returns True if test passed, False if assertion failed
    assert run_in_subprocess(isolated_test)
```

### `@skip_in_ci` Decorator

Skips tests in CI environments where kernel capabilities may be restricted.

**Usage**:
```python
from tests.compliance.bastion_test_helpers import skip_in_ci

@skip_in_ci
def test_seccomp_feature():
    # This test skips in GitHub Actions, GitLab CI, etc.
    # where seccomp may not be available
    pass
```

### `@requires_linux` Decorator

Skips tests on non-Linux platforms where seccomp-BPF is unavailable.

**Usage**:
```python
from tests.compliance.bastion_test_helpers import requires_linux

@requires_linux
def test_linux_specific_feature():
    # This test only runs on Linux
    pass
```

## Test Categories

### Unit Tests (No Subprocess Needed)

These tests don't call `enforce()` and don't need subprocess isolation:

```python
def test_create_policy():
    """Test policy creation - no enforcement"""
    policy = KernelPolicy(
        name="test",
        regulation="LGPD",
        blocked_syscalls=["open"],
    )

    assert policy.name == "test"
    # No enforce() call - no subprocess needed
```

### Enforcement Tests (Subprocess Required)

These tests call `enforce()` and **must** use subprocess isolation:

```python
@skip_in_ci
def test_policy_enforcement():
    """Test policy enforcement - needs subprocess"""

    def isolated_test():
        policy = KernelPolicy(
            name="test",
            regulation="LGPD",
            blocked_syscalls=["open"],
        )

        with policy.enforce():
            # Enforcement active - must be in subprocess
            pass

    assert run_in_subprocess(isolated_test)
```

### Integration Tests

Integration tests with BASTION should also use subprocess isolation:

```python
@skip_in_ci
def test_4layer_flow_with_bastion():
    """Test complete 4-layer flow including BASTION"""

    def isolated_test():
        from neutron.compliance.nexus_flow import NEXUSComplianceFlow

        flow = NEXUSComplianceFlow(enable_bastion=True)
        # Flow may call BASTION.enforce() internally
        response = await flow.validate(request)

    assert run_in_subprocess(isolated_test)
```

## Running Tests

### Run All Tests (Including BASTION)

```bash
# On Linux (outside CI)
pytest tests/compliance/test_bastion.py -v

# On macOS/Windows (simulated enforcement)
pytest tests/compliance/test_bastion.py -v

# In CI (enforcement tests skipped)
pytest tests/compliance/test_bastion.py -v
```

### Run Only Non-Enforcement Tests

```bash
# Skip tests that need subprocess isolation
pytest tests/compliance/test_bastion.py -v -m "not slow"
```

### Run with Coverage

```bash
# Coverage tracking works across subprocesses
pytest tests/compliance/test_bastion.py --cov=neutron.compliance.bastion
```

## CI Configuration

In CI environments (GitHub Actions, GitLab CI), enforcement tests are automatically skipped via `@skip_in_ci` decorator.

This prevents:
- ❌ Segfaults from seccomp restrictions
- ❌ Permission errors in containerized environments
- ❌ Flaky tests due to kernel feature availability

While still testing:
- ✅ Policy creation and validation
- ✅ BPF program generation
- ✅ Capability management
- ✅ Error handling

## Troubleshooting

### Test hangs indefinitely

**Cause**: Subprocess didn't exit properly

**Solution**: Check that test function doesn't have infinite loops or blocking I/O

### Test fails with "Operation not permitted"

**Cause**: `prctl(PR_SET_SECCOMP)` requires `CAP_SYS_ADMIN` or unprivileged seccomp support

**Solution**:
- Run with `@skip_in_ci` decorator
- Or run tests outside containers/CI
- Or enable unprivileged seccomp in kernel: `sysctl kernel.unprivileged_userns_clone=1`

### Segfault in test suite

**Cause**: Multiple tests applying conflicting seccomp filters in same process

**Solution**: Ensure all `enforce()` calls are wrapped in `run_in_subprocess()`

### ImportError for bastion_test_helpers

**Cause**: Helper module not in Python path

**Solution**: Run pytest from repo root: `pytest tests/compliance/test_bastion.py`

## Best Practices

### ✅ DO

- Use `run_in_subprocess()` for all tests calling `enforce()`
- Use `@skip_in_ci` for enforcement tests
- Test policy creation/validation without subprocess
- Document why subprocess isolation is needed

### ❌ DON'T

- Call `enforce()` directly in test suite without subprocess
- Assume seccomp is available in all environments
- Apply multiple filters in same test without isolation
- Forget to clean up capabilities (`revoke_capability()`)

## Example: Complete Test

```python
from tests.compliance.bastion_test_helpers import run_in_subprocess, skip_in_ci
from neutron.compliance.bastion import (
    KernelPolicy,
    ComplianceCapability,
    grant_capability,
    revoke_capability,
)

@skip_in_ci
def test_lgpd_consent_enforcement():
    """
    Test LGPD Article 7 consent enforcement at kernel level.

    This test must run in subprocess to isolate seccomp filter.
    """

    def isolated_test():
        # Create policy blocking file access without consent
        policy = KernelPolicy(
            name="lgpd_art7",
            regulation="LGPD",
            blocked_syscalls=["open", "openat", "read"],
            required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
            action="ERRNO",
            errno=13,  # EACCES
            audit=True,
        )

        # Test 1: Without consent, enforcement is active
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        with policy.enforce():
            assert not policy.check_capability()
            # Seccomp filter is now active (on Linux)
            # On non-Linux, simulated via environment variable

        # Test 2: With consent, enforcement is skipped
        grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

        with policy.enforce():
            assert policy.check_capability()
            # No seccomp filter applied

        # Cleanup
        revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

    # Run in isolated subprocess
    assert run_in_subprocess(isolated_test)
```

## See Also

- [BASTION Architecture](./architecture/BASTION.md)
- [4-Layer Compliance Flow](./architecture/4LAYER_FLOW.md)
- [pytest subprocess documentation](https://docs.pytest.org/en/stable/how-to/subprocess.html)
