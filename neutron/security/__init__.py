"""
Neutron Security Module — Build-Time & Supply-Chain Defense

Protects against the attack vector that bypasses all 4 NEXUS layers:
    .git hook poisoning → shellHook injection → machine compromise

Key capabilities:
    - Git hook scanner (detects non-standard hooks)
    - Git config integrity checker (url.insteadOf remapping)
    - Nix flake auditor (unpinned inputs, suspicious shellHooks)
    - Pre-build validation gate (hook that runs BEFORE nix develop)
"""

from neutron.security.git_scanner import GitConfigFinding, GitHookFinding, GitScanner
from neutron.security.nix_checker import FlakeFinding, NixFlakeChecker

__all__ = [
    "GitScanner",
    "GitHookFinding",
    "GitConfigFinding",
    "NixFlakeChecker",
    "FlakeFinding",
]
