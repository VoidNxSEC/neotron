"""
BASTION Landlock — Kernel-level file access control via Landlock LSM.

Unlike seccomp-bpf (which sees syscall numbers and register VALUES, not pointer
CONTENTS), Landlock operates at the INODE layer. This means it CAN resolve file
paths — closing the gap that the Red Team audit identified.

Architecture:
    Python Agent
        ↓
    SENTINEL (user-space policy)
        ↓
    Landlock Ruleset (kernel inode-level enforcement)
        ↓
    open('/data/client_A.json') → Landlock checks inode permissions
        ↓                          ↓
    ALLOWED (path in ruleset)    DENIED (EACCES)

Key properties:
    - Unprivileged: no CAP_SYS_ADMIN needed (kernel >= 5.13)
    - Per-process: rules apply to the calling process and all children
    - Irreversible: once restrict_self() is called, rules cannot be relaxed
    - Complements seccomp: seccomp filters syscalls, Landlock filters files

Syscall numbers (x86_64):
    landlock_create_ruleset  444
    landlock_add_rule        445
    landlock_restrict_self   446
"""

import ctypes
import errno
import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Landlock ABI constants (linux/landlock.h)
# ---------------------------------------------------------------------------

# Filesystem access rights
LANDLOCK_ACCESS_FS_EXECUTE = 1 << 0
LANDLOCK_ACCESS_FS_WRITE_FILE = 1 << 1
LANDLOCK_ACCESS_FS_READ_FILE = 1 << 2
LANDLOCK_ACCESS_FS_READ_DIR = 1 << 3
LANDLOCK_ACCESS_FS_REMOVE_DIR = 1 << 4
LANDLOCK_ACCESS_FS_REMOVE_FILE = 1 << 5
LANDLOCK_ACCESS_FS_MAKE_CHAR = 1 << 6
LANDLOCK_ACCESS_FS_MAKE_DIR = 1 << 7
LANDLOCK_ACCESS_FS_MAKE_REG = 1 << 8
LANDLOCK_ACCESS_FS_MAKE_SOCK = 1 << 9
LANDLOCK_ACCESS_FS_MAKE_FIFO = 1 << 10
LANDLOCK_ACCESS_FS_MAKE_BLOCK = 1 << 11
LANDLOCK_ACCESS_FS_MAKE_SYM = 1 << 12
LANDLOCK_ACCESS_FS_REFER = 1 << 13
LANDLOCK_ACCESS_FS_TRUNCATE = 1 << 14

# Common combinations
LANDLOCK_ACCESS_FS_READ = LANDLOCK_ACCESS_FS_READ_FILE | LANDLOCK_ACCESS_FS_READ_DIR

LANDLOCK_ACCESS_FS_WRITE = (
    LANDLOCK_ACCESS_FS_WRITE_FILE
    | LANDLOCK_ACCESS_FS_MAKE_DIR
    | LANDLOCK_ACCESS_FS_MAKE_REG
    | LANDLOCK_ACCESS_FS_MAKE_SYM
    | LANDLOCK_ACCESS_FS_REMOVE_DIR
    | LANDLOCK_ACCESS_FS_REMOVE_FILE
    | LANDLOCK_ACCESS_FS_TRUNCATE
)

LANDLOCK_ACCESS_FS_READ_WRITE = LANDLOCK_ACCESS_FS_READ | LANDLOCK_ACCESS_FS_WRITE

LANDLOCK_ACCESS_FS_ALL = (
    LANDLOCK_ACCESS_FS_EXECUTE
    | LANDLOCK_ACCESS_FS_WRITE_FILE
    | LANDLOCK_ACCESS_FS_READ_FILE
    | LANDLOCK_ACCESS_FS_READ_DIR
    | LANDLOCK_ACCESS_FS_REMOVE_DIR
    | LANDLOCK_ACCESS_FS_REMOVE_FILE
    | LANDLOCK_ACCESS_FS_MAKE_CHAR
    | LANDLOCK_ACCESS_FS_MAKE_DIR
    | LANDLOCK_ACCESS_FS_MAKE_REG
    | LANDLOCK_ACCESS_FS_MAKE_SOCK
    | LANDLOCK_ACCESS_FS_MAKE_FIFO
    | LANDLOCK_ACCESS_FS_MAKE_BLOCK
    | LANDLOCK_ACCESS_FS_MAKE_SYM
    | LANDLOCK_ACCESS_FS_REFER
    | LANDLOCK_ACCESS_FS_TRUNCATE
)

# Syscall numbers (x86_64)
_NR_landlock_create_ruleset = 444
_NR_landlock_add_rule = 445
_NR_landlock_restrict_self = 446

# Landlock rule types
LANDLOCK_RULE_PATH_BENEATH = 1

# ---------------------------------------------------------------------------
# ctypes syscall wrapper (bypasses glibc, calls kernel directly)
# ---------------------------------------------------------------------------
_libc = ctypes.CDLL(None, use_errno=True)


def _syscall(sysno: int, *args) -> int:
    """Raw Linux syscall via ctypes."""
    return _libc.syscall(sysno, *args)


@dataclass
class LandlockError(Exception):
    """Landlock operation failed."""

    message: str
    errno: int = 0

    def __str__(self):
        if self.errno:
            return f"Landlock: {self.message} (errno={self.errno}: {os.strerror(self.errno)})"
        return f"Landlock: {self.message}"


# ---------------------------------------------------------------------------
# Ruleset
# ---------------------------------------------------------------------------
@dataclass
class LandlockRule:
    """A single Landlock file access rule."""

    path: str
    access: int  # bitmask of LANDLOCK_ACCESS_FS_*
    beneath: bool = True  # If True, applies to path AND all subdirectories

    def __repr__(self):
        return f"LandlockRule({self.path!r}, access=0x{self.access:x})"


@dataclass
class LandlockProfile:
    """Named profile that defines allowed paths for an agent."""

    name: str
    description: str
    rules: list[LandlockRule] = field(default_factory=list)
    default_deny: bool = True  # If True, everything not in rules is denied

    def allow_read(self, path: str):
        """Allow reading from path and its children."""
        self.rules.append(LandlockRule(path, LANDLOCK_ACCESS_FS_READ))
        return self

    def allow_write(self, path: str):
        """Allow writing to path and its children."""
        self.rules.append(LandlockRule(path, LANDLOCK_ACCESS_FS_WRITE))
        return self

    def allow_read_write(self, path: str):
        """Allow read+write to path and its children."""
        self.rules.append(LandlockRule(path, LANDLOCK_ACCESS_FS_READ_WRITE))
        return self

    def allow_execute(self, path: str):
        """Allow execution from path."""
        self.rules.append(LandlockRule(path, LANDLOCK_ACCESS_FS_EXECUTE))
        return self

    def allow_all(self, path: str):
        """Allow all filesystem operations on path."""
        self.rules.append(LandlockRule(path, LANDLOCK_ACCESS_FS_ALL))
        return self


# ---------------------------------------------------------------------------
# Pre-defined profiles
# ---------------------------------------------------------------------------
def profile_readonly_data() -> LandlockProfile:
    """Agent can only read from /data. No write, no execute."""
    return LandlockProfile(
        name="readonly-data",
        description="Read-only access to /data. Blocks all writes and execution.",
    ).allow_read("/data")


def profile_api_server() -> LandlockProfile:
    """Minimal access for an API server process."""
    return (
        LandlockProfile(
            name="api-server",
            description="API server: read configs, write logs, no execution.",
        )
        .allow_read("/etc/neotron")
        .allow_read_write("/var/log/neotron")
        .allow_read("/usr/lib")
        .allow_read("/nix/store")  # Nix packages are read-only
    )


def profile_agent_sandbox() -> LandlockProfile:
    """Tight sandbox for untrusted agent execution."""
    return (
        LandlockProfile(
            name="agent-sandbox",
            description="Minimal sandbox: read from input dir, write to output dir only.",
        )
        .allow_read("/tmp/neotron/input")
        .allow_write("/tmp/neotron/output")
        # No access to /home, /etc, /proc, /sys, /dev
    )


def profile_compliance_auditor() -> LandlockProfile:
    """Compliance auditor: read-only access to data and audit trail."""
    return (
        LandlockProfile(
            name="compliance-auditor",
            description="Read-only: compliance data + audit trail. No modification allowed.",
        )
        .allow_read("/data")
        .allow_read("/var/audit")
        .allow_read("/nix/store")
        .allow_write("/var/log/neotron/audit.log")  # Only write to audit log
    )


# ---------------------------------------------------------------------------
# Core Landlock API
# ---------------------------------------------------------------------------
class LandlockEnforcer:
    """
    Create and enforce Landlock rulesets for the current process.

    Once enforce() is called, the process (and all children) are restricted
    to the paths specified in the profile. This is IRREVERSIBLE.
    """

    def __init__(self, profile: LandlockProfile):
        self.profile = profile
        self._ruleset_fd: int | None = None
        self._enforced: bool = False
        self._abi_version: int = self._detect_abi()

    @property
    def enforced(self) -> bool:
        return self._enforced

    # ------------------------------------------------------------------
    # ABI detection
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_abi() -> int:
        """
        Detect the maximum supported Landlock ABI version.

        Returns:
            0: Landlock not supported
            1: Initial ABI (kernel 5.13)
            2: Added REFER (kernel 5.19)
            3: Added TRUNCATE (kernel 6.2)
            4: Added IOCTL support (kernel 6.7)
        """
        try:
            result = _syscall(
                _NR_landlock_create_ruleset,
                ctypes.c_void_p(0),  # NULL attr
                0,  # size 0
                0,  # flags 0
            )
            if result < 0:
                err = ctypes.get_errno()
                if err == errno.EOPNOTSUPP:
                    return 0
                # EINVAL or other means it's supported but we passed bad args
                # Try to detect ABI version
                return 1  # Minimal version
            return 4  # Latest known
        except (OSError, AttributeError):
            return 0

    @staticmethod
    def supported() -> bool:
        """Check if Landlock is available on this kernel."""
        return LandlockEnforcer._detect_abi() > 0

    @staticmethod
    def check_no_new_privs() -> bool:
        """
        Check if the current process has NO_NEW_PRIVS set.

        This is required for landlock_restrict_self() to work.
        Returns True if the flag is set.
        """
        PR_GET_NO_NEW_PRIVS = 39
        try:
            result = _libc.prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0)
            return result == 1
        except Exception:
            return False

    @staticmethod
    def abi_version() -> int:
        """Get the Landlock ABI version."""
        return LandlockEnforcer._detect_abi()

    # ------------------------------------------------------------------
    # Enforcement
    # ------------------------------------------------------------------
    def enforce(self) -> None:
        """
        Apply Landlock rules to the current process.

        After this call:
        - Any file access outside the allowed paths returns EACCES
        - Rules are inherited by child processes
        - Rules CANNOT be relaxed (only further restricted)

        Raises:
            LandlockError: if Landlock is not available
            OSError: if the syscall fails
        """
        if self._enforced:
            raise LandlockError("Already enforced. Landlock is irreversible.")

        abi = self._detect_abi()
        if abi == 0:
            raise LandlockError("Landlock is not supported on this kernel (need >= 5.13)")

        # Step 0: Disable privilege escalation (required by kernel)
        # Without this, restrict_self returns EPERM.
        # IMPORTANT: On some kernel/LSM configurations, prctl(PR_SET_NO_NEW_PRIVS)
        # may silently fail. In that case, the process must be started with
        # NoNewPrivileges=yes in systemd, or via `setpriv --no-new-privs`.
        PR_SET_NO_NEW_PRIVS = 36
        PR_GET_NO_NEW_PRIVS = 39

        # Check if already set (e.g., by systemd)
        already_set = _libc.prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) == 1

        if not already_set:
            _libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
            # Verify it was set
            if _libc.prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) != 1:
                raise LandlockError(
                    "Cannot set NO_NEW_PRIVS. "
                    "This is required for Landlock. "
                    "Start the process with systemd NoNewPrivileges=yes "
                    "or via: setpriv --no-new-privs python ..."
                )

        # Step 1: Create ruleset with all access rights that we want to CONTROL
        handled_access = LANDLOCK_ACCESS_FS_ALL
        if abi < 2:
            handled_access &= ~LANDLOCK_ACCESS_FS_REFER
        if abi < 3:
            handled_access &= ~LANDLOCK_ACCESS_FS_TRUNCATE

        ruleset_attr = ctypes.c_uint64(handled_access)
        ruleset_fd = _syscall(
            _NR_landlock_create_ruleset,
            ctypes.byref(ruleset_attr),
            ctypes.sizeof(ruleset_attr),
            0,  # flags = 0
        )

        if ruleset_fd < 0:
            err = ctypes.get_errno()
            raise LandlockError(f"Failed to create ruleset: {os.strerror(err)}", err)

        self._ruleset_fd = ruleset_fd

        # Step 2: Add rules for each allowed path
        for rule in self.profile.rules:
            self._add_path_rule(rule)

        # Step 3: Enforce (IRREVERSIBLE)
        result = _syscall(_NR_landlock_restrict_self, self._ruleset_fd, 0)
        if result < 0:
            err = ctypes.get_errno()
            os.close(self._ruleset_fd)
            raise LandlockError(f"Failed to restrict self: {os.strerror(err)}", err)

        os.close(self._ruleset_fd)
        self._ruleset_fd = None
        self._enforced = True

    def _add_path_rule(self, rule: LandlockRule) -> None:
        """Add a path_beneath rule to the ruleset."""
        if self._ruleset_fd is None:
            raise LandlockError("Ruleset not created. Call enforce() first.")

        path = Path(rule.path).resolve()
        if not path.exists():
            raise LandlockError(f"Path does not exist: {rule.path}")

        # Open the directory as a file descriptor
        dir_fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)

        try:
            # The kernel needs a landlock_path_beneath_attr struct
            class LandlockPathBeneathAttr(ctypes.Structure):
                _fields_ = [
                    ("allowed_access", ctypes.c_uint64),
                    ("parent_fd", ctypes.c_int),
                ]

            attr = LandlockPathBeneathAttr(
                allowed_access=rule.access,
                parent_fd=dir_fd,
            )

            result = _syscall(
                _NR_landlock_add_rule,
                self._ruleset_fd,
                LANDLOCK_RULE_PATH_BENEATH,
                ctypes.byref(attr),
                0,  # flags = 0
            )

            if result < 0:
                err = ctypes.get_errno()
                raise LandlockError(f"Failed to add rule for {rule.path}: {os.strerror(err)}", err)
        finally:
            os.close(dir_fd)


# ---------------------------------------------------------------------------
# Convenience decorator
# ---------------------------------------------------------------------------
def sandboxed(profile: LandlockProfile):
    """
    Decorator that enforces a Landlock profile before running a function.

    Usage:
        @sandboxed(profile_agent_sandbox())
        def process_task(task_data):
            # This function can only read/write to allowed paths
            ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            LandlockEnforcer(profile).enforce()
            return func(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------
class LandlockedEnv:
    """
    Context manager that enforces Landlock for a code block.

    Usage:
        with LandlockedEnv(profile_agent_sandbox()):
            result = run_untrusted_code()
    """

    def __init__(self, profile: LandlockProfile):
        self.enforcer = LandlockEnforcer(profile)

    def __enter__(self):
        self.enforcer.enforce()
        return self

    def __exit__(self, *args):
        pass  # Landlock is irreversible, nothing to undo
