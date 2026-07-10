"""
Helper utilities for BASTION kernel-level compliance tests.

Provides subprocess isolation to prevent seccomp-BPF filter conflicts.
"""

import os
import sys
import traceback
from collections.abc import Callable
from typing import Any


def run_in_subprocess(test_func: Callable[[], Any]) -> bool:
    """
    Run a test function in an isolated subprocess.

    This prevents seccomp-BPF filters from affecting other tests.
    seccomp filters are permanent per-process but die with the subprocess.

    Args:
        test_func: Test function to run (should take no arguments)

    Returns:
        True if test passed, False otherwise

    Usage:
        def test_bastion_enforcement():
            def isolated_test():
                policy = KernelPolicy(...)
                with policy.enforce():
                    # Test code here
                    assert something

            assert run_in_subprocess(isolated_test)
    """
    if sys.platform != "linux":
        # On non-Linux, no subprocess needed (simulated enforcement)
        try:
            test_func()
            return True
        except AssertionError:
            return False
        except Exception as e:
            print(f"Test error: {e}", file=sys.stderr)
            traceback.print_exc()
            return False

    # On Linux, fork subprocess to isolate seccomp filter
    pid = os.fork()

    if pid == 0:
        # Child process
        try:
            test_func()
            # Test passed - exit with code 0
            os._exit(0)
        except AssertionError as e:
            # Test failed - print and exit with code 1
            print(f"Assertion failed: {e}", file=sys.stderr)
            os._exit(1)
        except Exception as e:
            # Test error - print and exit with code 2
            print(f"Test error: {e}", file=sys.stderr)
            traceback.print_exc()
            os._exit(2)
    else:
        # Parent process - wait for child
        _, status = os.waitpid(pid, 0)

        # Extract exit code
        exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 255

        if exit_code == 0:
            return True  # Test passed
        elif exit_code == 1:
            return False  # Test assertion failed
        else:
            # Test error
            raise RuntimeError(f"Subprocess test failed with code {exit_code}")


def requires_linux(test_func: Callable) -> Callable:
    """
    Decorator to skip tests that require Linux kernel features.

    Usage:
        @requires_linux
        def test_seccomp_enforcement():
            # This test only runs on Linux
            pass
    """
    import pytest

    if sys.platform != "linux":
        return pytest.mark.skip(reason="Requires Linux kernel")(test_func)
    return test_func


def skip_in_ci(test_func: Callable) -> Callable:
    """
    Decorator to skip tests in CI environments where kernel features may be restricted.

    Usage:
        @skip_in_ci
        def test_kernel_enforcement():
            # This test skips in CI
            pass
    """
    import pytest

    # Check for common CI environment variables
    is_ci = any(
        [
            os.getenv("CI") == "true",
            os.getenv("GITHUB_ACTIONS") == "true",
            os.getenv("GITLAB_CI") == "true",
            os.getenv("CIRCLECI") == "true",
            os.getenv("TRAVIS") == "true",
        ]
    )

    if is_ci:
        return pytest.mark.skip(reason="Skipped in CI (kernel restrictions)")(test_func)
    return test_func
