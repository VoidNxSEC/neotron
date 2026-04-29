"""
NEXUS Decentralized Storage Layer

Provides IPFS and Arweave integration for immutable compliance audit trails.

Defense-in-Depth Compliance Architecture:
- Layer 1: SENTINEL (Application - Python validation)
- Layer 2: BASTION (Kernel - seccomp-BPF syscalls)
- Layer 3: BASTION-SC (Smart Contract - on-chain enforcement)
- Layer 4: Audit Trail (IPFS + Arweave) ← This module

Usage:
    from neutron.storage import DecentralizedStorage

    storage = DecentralizedStorage()

    # Store audit log on IPFS (mutable, pinned)
    receipt = await storage.store_audit_log(log, permanent=False)

    # Store on Arweave (permanent, pay-once)
    receipt = await storage.store_audit_log(log, permanent=True)
"""

from neutron.storage.decentralized import (
    ComplianceLog,
    DecentralizedStorage,
    StorageReceipt,
    StorageType,
)

__all__ = [
    "DecentralizedStorage",
    "StorageReceipt",
    "StorageType",
    "ComplianceLog",
]
