"""
Namespace Isolation — Landlock profiles per workflow.

Provides per-workflow file access isolation using Landlock LSM,
ensuring that workflow A cannot read workflow B's files.

Architecture:
    ┌───────────────────────────────────────────────────────┐
    │              NAMESPACE ISOLATION                      │
    │                                                       │
    │  Workflow A              Workflow B                   │
    │  ┌──────────┐           ┌──────────┐                 │
    │  │ /var/lib/ │           │ /var/lib/ │                │
    │  │ neotron/  │           │ neotron/  │                │
    │  │ wf_A/     │           │ wf_B/     │                │
    │  │  ├─ data/ │           │  ├─ data/ │                │
    │  │  └─ logs/ │           │  └─ logs/ │                │
    │  └──────────┘           └──────────┘                 │
    │       │                      │                        │
    │  Landlock: R/W           Landlock: R/W                │
    │  → /var/lib/neotron/wf_A  → /var/lib/neotron/wf_B    │
    │  → /tmp/wf_A_*             → /tmp/wf_B_*              │
    │  ✗ /var/lib/neotron/wf_B  ✗ /var/lib/neotron/wf_A   │
    └───────────────────────────────────────────────────────┘

Isolation guarantees:
    - Workflows cannot read each other's data directories
    - Workflows cannot write to each other's directories
    - Workflows share only explicitly whitelisted paths (/usr, /lib, etc.)
    - Landlock is enforced before any workflow code runs
    - seccomp-bpf can add additional syscall restrictions

Compliance impact:
    - GDPR Art. 32: Appropriate technical measures for data security
    - LGPD Art. 46: Security measures for personal data processing
    - SOC 2 CC6.1: Logical access control
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from neutron.bastion.landlock import (
    LANDLOCK_ACCESS_FS_EXECUTE,
    LANDLOCK_ACCESS_FS_READ,
    LANDLOCK_ACCESS_FS_WRITE,
    LandlockEnforcer,
    LandlockProfile,
    LandlockRule,
)

logger = logging.getLogger("neutron.bastion.namespaces")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORKFLOW_BASE_DIR = Path(os.environ.get("NEUTRON_WORKFLOW_DIR", "/var/lib/neotron/workflows"))

# Paths that ALL workflows can read (shared libraries, configs)
SHARED_READONLY_PATHS: list[Path] = [
    Path("/usr"),
    Path("/lib"),
    Path("/lib64"),
    Path("/etc/ssl"),
    Path("/etc/neotron"),
]

# Paths that are explicitly forbidden for ALL workflows
FORBIDDEN_PATHS: list[Path] = [
    Path("/etc/shadow"),
    Path("/etc/ssh"),
    Path("/root"),
    Path("/home/kernelcore/.ssh"),
    Path("/home/kernelcore/.gnupg"),
]

# ---------------------------------------------------------------------------
# Workflow Namespace
# ---------------------------------------------------------------------------


@dataclass
class WorkflowNamespace:
    """
    An isolated filesystem namespace for a workflow.

    Each workflow gets its own data directory with Landlock-enforced
    boundaries. Other workflows cannot access this namespace's data,
    and this namespace cannot access other workflows' data.
    """

    workflow_id: str
    name: str
    data_dir: Path
    tmp_dir: Path
    logs_dir: Path

    # Additional paths this workflow CAN access (beyond data_dir)
    extra_read_paths: set[Path] = field(default_factory=set)
    extra_write_paths: set[Path] = field(default_factory=set)

    # Whether this workflow needs network access
    allow_network: bool = False

    def to_landlock_profile(self) -> LandlockProfile:
        """
        Convert this namespace to a Landlock profile.

        The profile grants:
        - R/W to data_dir, tmp_dir, logs_dir
        - R-only to shared system paths
        - Explicitly denies forbidden paths
        """
        profile = LandlockProfile(
            name=f"workflow-{self.workflow_id}",
            description=f"Workflow namespace: {self.name}",
            rules=[],
        )

        # ── Workflow-specific paths (R/W) ──
        for dir_path in [self.data_dir, self.tmp_dir, self.logs_dir]:
            profile.rules.append(
                LandlockRule(
                    path=str(dir_path),
                    access=LANDLOCK_ACCESS_FS_READ | LANDLOCK_ACCESS_FS_WRITE,
                )
            )

        # ── Shared read-only paths ──
        for dir_path in SHARED_READONLY_PATHS:
            if dir_path.exists() or True:  # Create rule even if path doesn't exist yet
                profile.rules.append(
                    LandlockRule(
                        path=str(dir_path),
                        access=LANDLOCK_ACCESS_FS_READ | LANDLOCK_ACCESS_FS_EXECUTE,
                    )
                )

        # ── Extra paths ──
        for dir_path in self.extra_read_paths:
            profile.rules.append(
                LandlockRule(
                    path=str(dir_path),
                    access=LANDLOCK_ACCESS_FS_READ,
                )
            )

        for dir_path in self.extra_write_paths:
            profile.rules.append(
                LandlockRule(
                    path=str(dir_path),
                    access=LANDLOCK_ACCESS_FS_READ | LANDLOCK_ACCESS_FS_WRITE,
                )
            )

        # ── Explicit denies ──
        # Landlock is allow-list, so these are implicitly denied.
        # We add explicit deny rules for auditing purposes.
        for dir_path in FORBIDDEN_PATHS:
            profile.rules.append(
                LandlockRule(
                    path=str(dir_path),
                    access=0,  # No access — explicit deny
                )
            )

        return profile

    def create_directories(self) -> None:
        """Create the workflow directory structure."""
        for d in [self.data_dir, self.tmp_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def enforce(self) -> bool:
        """
        Apply Landlock enforcement for this namespace.

        After this call, the current process (and all children)
        CANNOT access any paths not explicitly allowed.

        This is IRREVERSIBLE — Landlock rules cannot be relaxed.
        """
        self.create_directories()
        profile = self.to_landlock_profile()

        try:
            enforcer = LandlockEnforcer()
            enforcer.apply_profile(profile)
            logger.info(
                "Namespace enforced: workflow=%s (%s) — %d rules",
                self.workflow_id,
                self.name,
                len(profile.rules),
            )
            return True
        except Exception as e:
            logger.error("Failed to enforce namespace for %s: %s", self.workflow_id, e)
            return False


# ---------------------------------------------------------------------------
# Namespace Manager
# ---------------------------------------------------------------------------


class NamespaceManager:
    """
    Manages isolated filesystem namespaces for workflows.

    Usage:
        manager = NamespaceManager()
        ns = manager.create_namespace("wf-001", "Credit Scoring")
        ns.enforce()
        # ... workflow runs in isolation ...
    """

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or WORKFLOW_BASE_DIR
        self._namespaces: dict[str, WorkflowNamespace] = {}
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_namespace(
        self,
        workflow_id: str,
        name: str,
        extra_read: list[Path] | None = None,
        extra_write: list[Path] | None = None,
        allow_network: bool = False,
    ) -> WorkflowNamespace:
        """
        Create an isolated namespace for a workflow.

        Directory structure:
            {base_dir}/{workflow_id}/
                ├── data/    ← R/W, workflow-specific
                ├── tmp/     ← R/W, temporary files
                └── logs/    ← R/W, workflow logs
        """
        ns_dir = self.base_dir / workflow_id

        ns = WorkflowNamespace(
            workflow_id=workflow_id,
            name=name,
            data_dir=ns_dir / "data",
            tmp_dir=ns_dir / "tmp",
            logs_dir=ns_dir / "logs",
            extra_read_paths=set(extra_read or []),
            extra_write_paths=set(extra_write or []),
            allow_network=allow_network,
        )

        self._namespaces[workflow_id] = ns
        logger.info("Namespace created: %s (%s)", workflow_id, name)
        return ns

    def get_namespace(self, workflow_id: str) -> WorkflowNamespace | None:
        """Get an existing namespace by ID."""
        return self._namespaces.get(workflow_id)

    def list_namespaces(self) -> list[WorkflowNamespace]:
        """List all active namespaces."""
        return list(self._namespaces.values())

    def destroy_namespace(self, workflow_id: str) -> bool:
        """
        Remove a namespace and its data.

        Note: Landlock rules are process-scoped and IRREVERSIBLE.
        This only removes the directory structure.
        """
        ns = self._namespaces.pop(workflow_id, None)
        if ns is None:
            return False

        import shutil

        try:
            shutil.rmtree(ns.data_dir, ignore_errors=True)
            shutil.rmtree(ns.tmp_dir, ignore_errors=True)
            shutil.rmtree(ns.logs_dir, ignore_errors=True)
            logger.info("Namespace destroyed: %s", workflow_id)
            return True
        except Exception as e:
            logger.warning("Failed to destroy namespace %s: %s", workflow_id, e)
            return False


# ---------------------------------------------------------------------------
# Pre-defined profiles
# ---------------------------------------------------------------------------


def profile_sandbox(workflow_id: str, name: str) -> WorkflowNamespace:
    """
    Maximum isolation: only workflow directory + shared libraries.
    No network. No /tmp outside workflow dir.
    """
    return WorkflowNamespace(
        workflow_id=workflow_id,
        name=f"{name} (sandbox)",
        data_dir=WORKFLOW_BASE_DIR / workflow_id / "data",
        tmp_dir=WORKFLOW_BASE_DIR / workflow_id / "tmp",
        logs_dir=WORKFLOW_BASE_DIR / workflow_id / "logs",
        allow_network=False,
    )


def profile_networked(workflow_id: str, name: str) -> WorkflowNamespace:
    """Same as sandbox, but allows network access for API calls."""
    ns = profile_sandbox(workflow_id, name)
    ns.allow_network = True
    return ns


def profile_compliance(workflow_id: str, name: str) -> WorkflowNamespace:
    """
    Compliance auditor: can read all workflow data (for scanning)
    but cannot write to any workflow directory.
    """
    ns = profile_networked(workflow_id, f"{name} (compliance)")
    # Add read-only access to all workflow dirs
    ns.extra_read_paths.add(WORKFLOW_BASE_DIR)
    return ns


def profile_builder(workflow_id: str, name: str) -> WorkflowNamespace:
    """
    Build workflow: needs /nix/store read access + /tmp write.
    Used for Nix builds and IP Guard verification.
    """
    ns = profile_networked(workflow_id, f"{name} (builder)")
    ns.extra_read_paths.add(Path("/nix/store"))
    ns.extra_read_paths.add(Path("/nix/var"))
    ns.extra_write_paths.add(Path("/tmp"))
    return ns


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "NamespaceManager",
    "WorkflowNamespace",
    "profile_sandbox",
    "profile_networked",
    "profile_compliance",
    "profile_builder",
    "SHARED_READONLY_PATHS",
    "FORBIDDEN_PATHS",
]
