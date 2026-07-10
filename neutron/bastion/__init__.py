"""
BASTION — Kernel-Level Enforcement Layer

Implements defense-in-depth at the kernel level using:
    - Landlock LSM (inode-level file access control — RESOLVES PATHS)
    - seccomp-BPF (syscall filtering — complements Landlock)
    - Namespace isolation (future: per-workflow namespaces)

Unlike the original BASTION which relied solely on seccomp-bpf
(which sees syscall numbers and register VALUES, not pointer CONTENTS),
this module adds Landlock which operates at the INODE layer and CAN
resolve file paths — closing the gap identified in the Red Team audit.
"""

from neutron.bastion.landlock import (
    LANDLOCK_ACCESS_FS_ALL,
    LANDLOCK_ACCESS_FS_EXECUTE,
    LANDLOCK_ACCESS_FS_READ,
    LANDLOCK_ACCESS_FS_READ_WRITE,
    LANDLOCK_ACCESS_FS_WRITE,
    LandlockedEnv,
    LandlockEnforcer,
    LandlockError,
    LandlockProfile,
    LandlockRule,
    profile_agent_sandbox,
    profile_api_server,
    profile_compliance_auditor,
    profile_readonly_data,
    sandboxed,
)

__all__ = [
    "LandlockEnforcer",
    "LandlockError",
    "LandlockProfile",
    "LandlockRule",
    "LandlockedEnv",
    "sandboxed",
    "profile_readonly_data",
    "profile_api_server",
    "profile_agent_sandbox",
    "profile_compliance_auditor",
    "LANDLOCK_ACCESS_FS_READ",
    "LANDLOCK_ACCESS_FS_WRITE",
    "LANDLOCK_ACCESS_FS_EXECUTE",
    "LANDLOCK_ACCESS_FS_READ_WRITE",
    "LANDLOCK_ACCESS_FS_ALL",
]
