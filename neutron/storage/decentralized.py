"""
Decentralized Storage Implementation

Provides IPFS and Arweave integration for immutable compliance audit trails.

IPFS: Fast, mutable, requires pinning (~$5/month for 100GB)
Arweave: Permanent, pay-once, immutable forever (~$0.005/MB one-time)

Design Philosophy:
- IPFS for development/testing and mutable audit logs
- Arweave for production critical logs (permanent storage)
- Content-addressed (CID-based) for integrity verification
- Supports both local IPFS daemon and Infura/Pinata
"""

import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

try:
    import ipfshttpclient
    IPFS_AVAILABLE = True
except ImportError:
    IPFS_AVAILABLE = False

try:
    import ar
    ARWEAVE_AVAILABLE = True
except ImportError:
    ARWEAVE_AVAILABLE = False


class StorageType(str, Enum):
    """Storage backend type"""
    IPFS = "ipfs"
    ARWEAVE = "arweave"
    LOCAL = "local"  # For testing


@dataclass
class StorageReceipt:
    """Receipt from storing data on decentralized storage"""
    storage_type: StorageType
    identifier: str  # CID for IPFS, TX ID for Arweave
    permanent: bool
    url: str
    timestamp: int
    size_bytes: int
    cost_usd: Optional[float] = None


@dataclass
class ComplianceLog:
    """Compliance audit log structure"""
    log_id: str
    user_address: str
    regulation: str  # "LGPD", "GDPR", "AI_ACT"
    article: int
    action: str  # "consent_granted", "consent_revoked", etc.
    passed: bool
    violation: Optional[str] = None
    timestamp: int = None
    metadata: Optional[Dict[str, Any]] = None
    blockchain_tx: Optional[str] = None  # Transaction hash if on-chain

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(time.time())

    def to_json(self) -> str:
        """Serialize to JSON for storage"""
        return json.dumps({
            "log_id": self.log_id,
            "user_address": self.user_address,
            "regulation": self.regulation,
            "article": self.article,
            "action": self.action,
            "passed": self.passed,
            "violation": self.violation,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "blockchain_tx": self.blockchain_tx,
        }, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ComplianceLog":
        """Deserialize from JSON"""
        data = json.loads(json_str)
        return cls(**data)


class DecentralizedStorage:
    """
    Decentralized storage client for IPFS and Arweave

    Usage:
        storage = DecentralizedStorage()

        # IPFS (mutable, fast)
        receipt = await storage.store_on_ipfs(log)

        # Arweave (permanent, slow but forever)
        receipt = await storage.store_on_arweave(log)

        # Auto-select based on permanent flag
        receipt = await storage.store_audit_log(log, permanent=True)
    """

    def __init__(
        self,
        ipfs_addr: str = "/ip4/127.0.0.1/tcp/5001",
        arweave_wallet_path: Optional[str] = None,
        use_infura: bool = False,
        infura_project_id: Optional[str] = None,
        infura_project_secret: Optional[str] = None,
    ):
        """
        Initialize decentralized storage client

        Args:
            ipfs_addr: IPFS daemon address (default: local)
            arweave_wallet_path: Path to Arweave wallet JWK file
            use_infura: Use Infura for IPFS instead of local daemon
            infura_project_id: Infura project ID (required if use_infura=True)
            infura_project_secret: Infura project secret
        """
        self.ipfs_client = None
        self.arweave_wallet = None
        self.use_infura = use_infura

        # Initialize IPFS client
        if IPFS_AVAILABLE:
            try:
                if use_infura and infura_project_id:
                    # Infura IPFS endpoint
                    self.ipfs_client = ipfshttpclient.connect(
                        f"/dns/ipfs.infura.io/tcp/5001/https",
                        auth=(infura_project_id, infura_project_secret)
                    )
                else:
                    # Local IPFS daemon
                    self.ipfs_client = ipfshttpclient.connect(ipfs_addr)
            except Exception as e:
                print(f"Warning: IPFS client not available: {e}")

        # Initialize Arweave wallet
        if ARWEAVE_AVAILABLE and arweave_wallet_path:
            try:
                with open(arweave_wallet_path, 'r') as f:
                    self.arweave_wallet = ar.Wallet(f.read())
            except Exception as e:
                print(f"Warning: Arweave wallet not available: {e}")

    async def store_audit_log(
        self,
        log: ComplianceLog,
        permanent: bool = False
    ) -> StorageReceipt:
        """
        Store compliance audit log on decentralized storage

        Args:
            log: Compliance log to store
            permanent: If True, use Arweave (permanent); else IPFS (mutable)

        Returns:
            StorageReceipt with CID/TX ID and access URL
        """
        if permanent:
            return await self.store_on_arweave(log)
        else:
            return await self.store_on_ipfs(log)

    async def store_on_ipfs(self, log: ComplianceLog) -> StorageReceipt:
        """
        Store log on IPFS (mutable, requires pinning)

        Advantages:
        - Fast upload (~1-2 seconds)
        - Can update by unpinning old version
        - Cheaper for temporary data

        Disadvantages:
        - Requires pinning service or own node
        - Not permanent by default
        - Costs ~$5/month per 100GB
        """
        if not self.ipfs_client:
            # Fallback to local storage for testing
            return self._store_local(log)

        try:
            # Serialize log to JSON
            json_data = log.to_json()
            size_bytes = len(json_data.encode('utf-8'))

            # Add to IPFS
            result = self.ipfs_client.add_json(json.loads(json_data))
            cid = result

            # Pin to ensure persistence
            self.ipfs_client.pin.add(cid)

            # Generate gateway URL
            if self.use_infura:
                url = f"https://ipfs.infura.io/ipfs/{cid}"
            else:
                url = f"https://ipfs.io/ipfs/{cid}"

            return StorageReceipt(
                storage_type=StorageType.IPFS,
                identifier=cid,
                permanent=False,
                url=url,
                timestamp=int(time.time()),
                size_bytes=size_bytes,
                cost_usd=None  # IPFS pinning cost varies
            )

        except Exception as e:
            print(f"Error storing on IPFS: {e}")
            # Fallback to local storage
            return self._store_local(log)

    async def store_on_arweave(self, log: ComplianceLog) -> StorageReceipt:
        """
        Store log on Arweave (permanent, pay-once-store-forever)

        Advantages:
        - Permanent storage (200+ years guaranteed)
        - Pay once (~$0.005/MB)
        - Immutable and censorship-resistant

        Disadvantages:
        - Slower upload (~30-60 seconds for confirmation)
        - Cannot update (truly immutable)
        - Requires AR tokens for payment
        """
        if not self.arweave_wallet:
            print("Warning: Arweave wallet not configured, falling back to IPFS")
            return await self.store_on_ipfs(log)

        try:
            # Serialize log to JSON
            json_data = log.to_json()
            data_bytes = json_data.encode('utf-8')
            size_bytes = len(data_bytes)

            # Create Arweave transaction
            transaction = ar.Transaction(
                self.arweave_wallet,
                data=data_bytes,
                tags=[
                    ar.Tag("Content-Type", "application/json"),
                    ar.Tag("App-Name", "NEXUS-Compliance"),
                    ar.Tag("Regulation", log.regulation),
                    ar.Tag("Article", str(log.article)),
                    ar.Tag("Log-ID", log.log_id),
                ]
            )

            # Sign transaction
            transaction.sign()

            # Send to Arweave network
            transaction.send()

            # Calculate cost (Arweave pricing: ~$0.005/MB)
            cost_usd = (size_bytes / 1_000_000) * 0.005

            return StorageReceipt(
                storage_type=StorageType.ARWEAVE,
                identifier=transaction.id,
                permanent=True,
                url=f"https://arweave.net/{transaction.id}",
                timestamp=int(time.time()),
                size_bytes=size_bytes,
                cost_usd=cost_usd
            )

        except Exception as e:
            print(f"Error storing on Arweave: {e}")
            # Fallback to IPFS
            return await self.store_on_ipfs(log)

    def _store_local(self, log: ComplianceLog) -> StorageReceipt:
        """
        Fallback: Store locally for testing/development

        Creates a local file with the log data for testing purposes
        when IPFS/Arweave are not available.
        """
        import hashlib
        import os

        # Create local storage directory
        storage_dir = "/tmp/nexus_audit_logs"
        os.makedirs(storage_dir, exist_ok=True)

        # Serialize log
        json_data = log.to_json()
        data_bytes = json_data.encode('utf-8')

        # Generate "CID" (hash of content)
        cid = hashlib.sha256(data_bytes).hexdigest()

        # Write to file
        file_path = os.path.join(storage_dir, f"{cid}.json")
        with open(file_path, 'w') as f:
            f.write(json_data)

        return StorageReceipt(
            storage_type=StorageType.LOCAL,
            identifier=cid,
            permanent=False,
            url=f"file://{file_path}",
            timestamp=int(time.time()),
            size_bytes=len(data_bytes),
            cost_usd=0.0
        )

    async def retrieve_log(
        self,
        storage_type: StorageType,
        identifier: str
    ) -> ComplianceLog:
        """
        Retrieve compliance log from decentralized storage

        Args:
            storage_type: IPFS or ARWEAVE
            identifier: CID (IPFS) or TX ID (Arweave)

        Returns:
            ComplianceLog object
        """
        if storage_type == StorageType.IPFS:
            return await self._retrieve_from_ipfs(identifier)
        elif storage_type == StorageType.ARWEAVE:
            return await self._retrieve_from_arweave(identifier)
        elif storage_type == StorageType.LOCAL:
            return self._retrieve_local(identifier)
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")

    async def _retrieve_from_ipfs(self, cid: str) -> ComplianceLog:
        """Retrieve log from IPFS by CID"""
        if not self.ipfs_client:
            return self._retrieve_local(cid)

        try:
            json_data = self.ipfs_client.cat(cid).decode('utf-8')
            return ComplianceLog.from_json(json_data)
        except Exception as e:
            raise ValueError(f"Failed to retrieve from IPFS: {e}")

    async def _retrieve_from_arweave(self, tx_id: str) -> ComplianceLog:
        """Retrieve log from Arweave by transaction ID"""
        try:
            import requests
            response = requests.get(f"https://arweave.net/{tx_id}")
            response.raise_for_status()
            return ComplianceLog.from_json(response.text)
        except Exception as e:
            raise ValueError(f"Failed to retrieve from Arweave: {e}")

    def _retrieve_local(self, identifier: str) -> ComplianceLog:
        """Retrieve log from local storage"""
        import os

        file_path = f"/tmp/nexus_audit_logs/{identifier}.json"
        if not os.path.exists(file_path):
            raise ValueError(f"Log not found: {identifier}")

        with open(file_path, 'r') as f:
            json_data = f.read()

        return ComplianceLog.from_json(json_data)

    def estimate_cost(
        self,
        size_bytes: int,
        storage_type: StorageType,
        duration_months: int = 12
    ) -> float:
        """
        Estimate storage cost

        Args:
            size_bytes: Size of data in bytes
            storage_type: IPFS or ARWEAVE
            duration_months: Duration for IPFS (ignored for Arweave)

        Returns:
            Estimated cost in USD
        """
        if storage_type == StorageType.IPFS:
            # IPFS pinning: ~$5/month per 100GB
            gb = size_bytes / 1_000_000_000
            cost_per_month = (gb / 100) * 5.0
            return cost_per_month * duration_months

        elif storage_type == StorageType.ARWEAVE:
            # Arweave: ~$0.005/MB one-time
            mb = size_bytes / 1_000_000
            return mb * 0.005

        else:
            return 0.0
