"""
BASTION Seccomp — Kernel-level syscall OBSERVABILITY via seccomp-BPF.

Where `neutron.compliance.bastion` uses seccomp to BLOCK syscalls (returning
EPERM / killing the thread), this module uses seccomp to OBSERVE them
non-destructively. A matched syscall returns SECCOMP_RET_LOG: the kernel
records the event through the audit subsystem (auditd / dmesg) and then lets
the syscall proceed. The workload is never interrupted.

This closes the observability side of BASTION's stated architecture:

    Landlock  → inode-level file access control   (neutron.bastion.landlock)
    seccomp   → syscall-level observability        (THIS MODULE)
    namespaces→ process/resource isolation          (neutron.bastion.namespaces)

Why RET_LOG instead of ptrace/eBPF:
    - Unprivileged: needs only PR_SET_NO_NEW_PRIVS, no CAP_SYS_ADMIN, no BPF fd.
    - Per-process + inherited by children, exactly like the Landlock model.
    - Zero-overhead on the fast path: unmatched syscalls hit RET_ALLOW directly.
    - Fail-open by design: if the kernel/audit does not honor "log", RET_LOG is
      treated as RET_ALLOW, so installing an observer can never break a workload.

Key properties:
    - Kernel >= 4.14 for SECCOMP_RET_LOG.
    - Irreversible: once installed, the filter stays for the process lifetime.
    - Observability only — this module never denies. Denial lives in the
      compliance layer; keeping the two apart avoids accidental kills from a
      tool whose only job is to watch.

BPF filter shape (x86_64):
    load  arch
    jeq   AUDIT_ARCH_X86_64 ? continue : ALLOW      # never interfere off-arch
    load  nr
    jeq   <observed syscall> ? LOG : next
    ...
    ALLOW
    LOG
"""

import ctypes
import errno
import os
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# seccomp / BPF ABI constants (linux/seccomp.h, linux/filter.h, linux/audit.h)
# ---------------------------------------------------------------------------

# prctl options
PR_SET_NO_NEW_PRIVS = 38
PR_GET_NO_NEW_PRIVS = 39
PR_SET_SECCOMP = 22
PR_GET_SECCOMP = 21

# seccomp modes
SECCOMP_MODE_FILTER = 2

# BPF instruction classes / modifiers
BPF_LD = 0x00
BPF_W = 0x00
BPF_ABS = 0x20
BPF_JMP = 0x05
BPF_JEQ = 0x10
BPF_K = 0x00
BPF_RET = 0x06

# Composed opcodes
_LD_W_ABS = BPF_LD | BPF_W | BPF_ABS  # 0x20 — load 32-bit word at absolute offset
_JEQ_K = BPF_JMP | BPF_JEQ | BPF_K  # 0x15 — jump if A == K
_RET_K = BPF_RET | BPF_K  # 0x06 — return constant

# seccomp return actions
SECCOMP_RET_ALLOW = 0x7FFF0000
SECCOMP_RET_LOG = 0x7FFC0000  # kernel >= 4.14: log then allow
SECCOMP_RET_USER_NOTIF = 0x7FC00000  # kernel >= 5.0: hand off to a supervisor

# Architecture token
AUDIT_ARCH_X86_64 = 0xC000003E

# Offsets into `struct seccomp_data`
_OFF_NR = 0
_OFF_ARCH = 4

# ---------------------------------------------------------------------------
# Curated x86_64 syscall table — the security-relevant surface worth observing.
# (Not exhaustive: the point is a meaningful, named subset, not every syscall.)
# ---------------------------------------------------------------------------
SYSCALLS_X86_64: dict[str, int] = {
    # filesystem
    "read": 0,
    "write": 1,
    "open": 2,
    "close": 3,
    "stat": 4,
    "openat": 257,
    "unlink": 87,
    "unlinkat": 263,
    "rename": 82,
    "renameat": 264,
    "renameat2": 316,
    "chmod": 90,
    "fchmod": 91,
    "fchmodat": 268,
    "chown": 92,
    "truncate": 76,
    "getdents64": 217,
    # network
    "socket": 41,
    "connect": 42,
    "accept": 43,
    "accept4": 288,
    "bind": 49,
    "listen": 50,
    "sendto": 44,
    "recvfrom": 45,
    "sendmsg": 46,
    "recvmsg": 47,
    # process / execution
    "execve": 59,
    "execveat": 322,
    "fork": 57,
    "vfork": 58,
    "clone": 56,
    "clone3": 435,
    "kill": 62,
    "ptrace": 101,
    # privilege / capabilities
    "setuid": 105,
    "setgid": 106,
    "setreuid": 113,
    "setregid": 114,
    "capset": 126,
    "prctl": 157,
    "seccomp": 317,
    "bpf": 321,
    # kernel / module surface (high-signal for tamper detection)
    "init_module": 175,
    "finit_module": 313,
    "delete_module": 176,
    "mount": 165,
    "umount2": 166,
    "reboot": 169,
    "kexec_load": 246,
}

# Named groups for building profiles.
GROUP_FILESYSTEM = (
    "open",
    "openat",
    "unlink",
    "unlinkat",
    "rename",
    "renameat",
    "renameat2",
    "chmod",
    "fchmod",
    "fchmodat",
    "chown",
    "truncate",
)
GROUP_NETWORK = (
    "socket",
    "connect",
    "accept",
    "accept4",
    "bind",
    "listen",
    "sendto",
    "recvfrom",
    "sendmsg",
    "recvmsg",
)
GROUP_EXEC = ("execve", "execveat", "fork", "vfork", "clone", "clone3", "ptrace")
GROUP_PRIVILEGE = (
    "setuid",
    "setgid",
    "setreuid",
    "setregid",
    "capset",
    "prctl",
    "seccomp",
    "bpf",
)
GROUP_KERNEL = (
    "init_module",
    "finit_module",
    "delete_module",
    "mount",
    "umount2",
    "reboot",
    "kexec_load",
)


# ---------------------------------------------------------------------------
# ctypes syscall / prctl plumbing (calls kernel directly, like landlock.py)
# ---------------------------------------------------------------------------
_libc = ctypes.CDLL(None, use_errno=True)


class _SockFilter(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_uint16),
        ("jt", ctypes.c_uint8),
        ("jf", ctypes.c_uint8),
        ("k", ctypes.c_uint32),
    ]


class _SockFprog(ctypes.Structure):
    _fields_ = [
        ("len", ctypes.c_uint16),
        ("filter", ctypes.POINTER(_SockFilter)),
    ]


@dataclass
class SeccompError(Exception):
    """A seccomp observability operation failed."""

    message: str
    errno: int = 0

    def __str__(self) -> str:
        if self.errno:
            return f"Seccomp: {self.message} (errno={self.errno}: {os.strerror(self.errno)})"
        return f"Seccomp: {self.message}"


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@dataclass
class SeccompProfile:
    """Named set of syscalls to observe for a process."""

    name: str
    description: str = ""
    syscalls: set[str] = field(default_factory=set)
    # Action for matched syscalls. RET_LOG = observe-and-allow (the default and
    # only non-destructive option). RET_USER_NOTIF is exposed for a future live
    # supervisor but requires a listener process to drain notifications.
    action: int = SECCOMP_RET_LOG

    def observe(self, *names: str) -> "SeccompProfile":
        """Add individual syscalls by name."""
        for n in names:
            if n not in SYSCALLS_X86_64:
                raise SeccompError(f"unknown syscall: {n!r}")
            self.syscalls.add(n)
        return self

    def observe_filesystem(self) -> "SeccompProfile":
        return self.observe(*GROUP_FILESYSTEM)

    def observe_network(self) -> "SeccompProfile":
        return self.observe(*GROUP_NETWORK)

    def observe_exec(self) -> "SeccompProfile":
        return self.observe(*GROUP_EXEC)

    def observe_privilege(self) -> "SeccompProfile":
        return self.observe(*GROUP_PRIVILEGE)

    def observe_kernel(self) -> "SeccompProfile":
        return self.observe(*GROUP_KERNEL)

    def syscall_numbers(self) -> list[int]:
        """Resolved, de-duplicated, deterministically ordered syscall numbers."""
        return sorted({SYSCALLS_X86_64[n] for n in self.syscalls})


# ---------------------------------------------------------------------------
# Pre-defined profiles
# ---------------------------------------------------------------------------
def profile_observe_filesystem() -> SeccompProfile:
    """Log every file open/mutation an agent performs."""
    return SeccompProfile(
        name="observe-filesystem",
        description="Log file open/rename/unlink/chmod/chown by the agent.",
    ).observe_filesystem()


def profile_observe_network() -> SeccompProfile:
    """Log socket/connect/bind activity — data egress visibility."""
    return SeccompProfile(
        name="observe-network",
        description="Log socket/connect/bind/send/recv by the agent.",
    ).observe_network()


def profile_observe_exec() -> SeccompProfile:
    """Log process creation and ptrace — spawn/inspection visibility."""
    return SeccompProfile(
        name="observe-exec",
        description="Log execve/fork/clone/ptrace by the agent.",
    ).observe_exec()


def profile_observe_sensitive() -> SeccompProfile:
    """Full BASTION observability surface: fs + net + exec + privilege + kernel."""
    p = SeccompProfile(
        name="observe-sensitive",
        description="Log the full security-relevant syscall surface.",
    )
    return (
        p.observe_filesystem().observe_network().observe_exec().observe_privilege().observe_kernel()
    )


# ---------------------------------------------------------------------------
# BPF program builder
# ---------------------------------------------------------------------------
def build_filter(syscall_numbers: list[int], action: int = SECCOMP_RET_LOG) -> list[_SockFilter]:
    """
    Build a seccomp-BPF program that returns `action` for each observed syscall
    and SECCOMP_RET_ALLOW for everything else. Off-architecture syscalls are
    always allowed (never interfered with).

    Layout (indices), M = len(syscall_numbers):
        0            load arch
        1            jeq AUDIT_ARCH_X86_64 ? next : ALLOW
        2            load nr
        3 .. 3+M-1   jeq <sysno> ? ACTION : fallthrough
        3+M          ALLOW
        3+M+1        ACTION
    """
    m = len(syscall_numbers)
    idx_allow = 3 + m
    idx_action = 3 + m + 1
    prog: list[_SockFilter] = []

    # 0: load the arch field
    prog.append(_SockFilter(_LD_W_ABS, 0, 0, _OFF_ARCH))
    # 1: if arch mismatches, jump straight to ALLOW (do not interfere)
    prog.append(_SockFilter(_JEQ_K, 0, idx_allow - 2, AUDIT_ARCH_X86_64))
    # 2: load the syscall number
    prog.append(_SockFilter(_LD_W_ABS, 0, 0, _OFF_NR))
    # 3 .. : one comparison per observed syscall, jump to ACTION on match
    for j, nr in enumerate(syscall_numbers):
        here = 3 + j
        jt = idx_action - (here + 1)
        prog.append(_SockFilter(_JEQ_K, jt, 0, nr))
    # ALLOW (default) then ACTION (matched)
    prog.append(_SockFilter(_RET_K, 0, 0, SECCOMP_RET_ALLOW))
    prog.append(_SockFilter(_RET_K, 0, 0, action))
    return prog


# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------
class SeccompObserver:
    """
    Install a non-destructive seccomp-BPF observer for the current process.

    Matched syscalls are logged by the kernel (RET_LOG) and then allowed.
    Installation is irreversible for the process lifetime and inherited by
    children — the same model as Landlock.
    """

    def __init__(self, profile: SeccompProfile):
        self.profile = profile
        self._installed = False

    @property
    def installed(self) -> bool:
        return self._installed

    # -- capability detection ------------------------------------------------
    @staticmethod
    def supported() -> bool:
        """True if the kernel exposes seccomp filter mode."""
        try:
            # PR_GET_SECCOMP returns the current mode (>=0) when supported.
            return _libc.prctl(PR_GET_SECCOMP, 0, 0, 0, 0) >= 0
        except OSError:
            return False

    @staticmethod
    def actions_available() -> set[str]:
        """Seccomp actions the kernel advertises as available."""
        try:
            with open("/proc/sys/kernel/seccomp/actions_avail") as fh:
                return set(fh.read().split())
        except OSError:
            return set()

    @classmethod
    def log_supported(cls) -> bool:
        """True if RET_LOG will actually be recorded (kernel >= 4.14 + audit)."""
        return "log" in cls.actions_available()

    @staticmethod
    def check_no_new_privs() -> bool:
        try:
            return _libc.prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) == 1
        except OSError:
            return False

    # -- installation --------------------------------------------------------
    def install(self) -> None:
        """
        Compile the profile to BPF and install it on the current process.

        Raises:
            SeccompError: if seccomp is unavailable, NO_NEW_PRIVS cannot be set,
                or the kernel rejects the filter.
        """
        if self._installed:
            raise SeccompError("Already installed. seccomp filters are irreversible.")

        if not self.supported():
            raise SeccompError("seccomp filter mode not supported on this kernel")

        numbers = self.profile.syscall_numbers()
        if not numbers:
            raise SeccompError("profile observes no syscalls")

        # NO_NEW_PRIVS is required to install a filter without CAP_SYS_ADMIN.
        if not self.check_no_new_privs():
            _libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
            if not self.check_no_new_privs():
                raise SeccompError(
                    "cannot set NO_NEW_PRIVS (required for seccomp). "
                    "Start under systemd NoNewPrivileges=yes or "
                    "`setpriv --no-new-privs ...`."
                )

        instrs = build_filter(numbers, self.profile.action)
        filt = (_SockFilter * len(instrs))(*instrs)
        fprog = _SockFprog(len(instrs), ctypes.cast(filt, ctypes.POINTER(_SockFilter)))

        rc = _libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(fprog), 0, 0)
        if rc != 0:
            err = ctypes.get_errno() or errno.EINVAL
            raise SeccompError("failed to install seccomp filter", err)

        self._installed = True


# ---------------------------------------------------------------------------
# Decorator + context manager (mirror the landlock ergonomics)
# ---------------------------------------------------------------------------
def observed(profile: SeccompProfile):
    """
    Decorator that installs a seccomp observer before running a function.

    Usage:
        @observed(profile_observe_network())
        def run_agent(task):
            ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            SeccompObserver(profile).install()
            return func(*args, **kwargs)

        return wrapper

    return decorator


class ObservedEnv:
    """
    Context manager that installs a seccomp observer for a code block.

    Usage:
        with ObservedEnv(profile_observe_sensitive()):
            run_untrusted_code()

    Note: seccomp is irreversible, so the filter persists after the block.
    """

    def __init__(self, profile: SeccompProfile):
        self.observer = SeccompObserver(profile)

    def __enter__(self):
        self.observer.install()
        return self

    def __exit__(self, *args):
        pass  # seccomp is irreversible; nothing to undo
