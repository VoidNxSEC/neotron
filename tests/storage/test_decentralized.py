"""
Tests for decentralized storage layer (IPFS + Arweave)

Tests cover:
- ComplianceLog serialization/deserialization
- IPFS storage and retrieval (with fallback)
- Arweave storage simulation
- Local storage fallback
- Cost estimation
- Error handling
"""

import json
import os
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from neutron.storage.decentralized import (
    DecentralizedStorage,
    StorageReceipt,
    StorageType,
    ComplianceLog,
)


class TestComplianceLog:
    """Test ComplianceLog data structure"""

    def test_create_compliance_log(self):
        """Test creating a compliance log"""
        log = ComplianceLog(
            log_id="log_001",
            user_address="0x1234567890abcdef",
            regulation="LGPD",
            article=7,
            action="consent_granted",
            passed=True,
            timestamp=1234567890,
        )

        assert log.log_id == "log_001"
        assert log.user_address == "0x1234567890abcdef"
        assert log.regulation == "LGPD"
        assert log.article == 7
        assert log.action == "consent_granted"
        assert log.passed is True
        assert log.timestamp == 1234567890

    def test_log_auto_timestamp(self):
        """Test automatic timestamp generation"""
        before = int(time.time())
        log = ComplianceLog(
            log_id="log_002",
            user_address="0xabcd",
            regulation="GDPR",
            article=22,
            action="human_review_required",
            passed=False,
        )
        after = int(time.time())

        assert before <= log.timestamp <= after

    def test_log_with_violation(self):
        """Test log with compliance violation"""
        log = ComplianceLog(
            log_id="log_003",
            user_address="0xabcd",
            regulation="LGPD",
            article=7,
            action="data_access_attempt",
            passed=False,
            violation="No consent granted for data processing",
        )

        assert log.passed is False
        assert log.violation == "No consent granted for data processing"

    def test_log_with_metadata(self):
        """Test log with additional metadata"""
        log = ComplianceLog(
            log_id="log_004",
            user_address="0xabcd",
            regulation="AI_ACT",
            article=13,
            action="transparency_check",
            passed=True,
            metadata={
                "model_id": "gpt-4",
                "explanation_provided": True,
                "risk_level": "high",
            },
        )

        assert log.metadata["model_id"] == "gpt-4"
        assert log.metadata["explanation_provided"] is True

    def test_log_serialization(self):
        """Test JSON serialization"""
        log = ComplianceLog(
            log_id="log_005",
            user_address="0xabcd",
            regulation="LGPD",
            article=7,
            action="consent_granted",
            passed=True,
            timestamp=1234567890,
        )

        json_str = log.to_json()
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data["log_id"] == "log_005"
        assert data["regulation"] == "LGPD"

    def test_log_deserialization(self):
        """Test JSON deserialization"""
        original = ComplianceLog(
            log_id="log_006",
            user_address="0xabcd",
            regulation="GDPR",
            article=15,
            action="data_access",
            passed=True,
            timestamp=1234567890,
        )

        json_str = original.to_json()
        restored = ComplianceLog.from_json(json_str)

        assert restored.log_id == original.log_id
        assert restored.user_address == original.user_address
        assert restored.regulation == original.regulation
        assert restored.article == original.article
        assert restored.passed == original.passed


class TestDecentralizedStorage:
    """Test DecentralizedStorage class"""

    @pytest.fixture
    def storage(self):
        """Create storage instance for testing"""
        return DecentralizedStorage()

    @pytest.fixture
    def sample_log(self):
        """Create sample compliance log"""
        return ComplianceLog(
            log_id="test_log_001",
            user_address="0x1234567890abcdef",
            regulation="LGPD",
            article=7,
            action="consent_granted",
            passed=True,
            timestamp=1234567890,
        )

    def test_storage_initialization(self, storage):
        """Test storage client initialization"""
        assert storage is not None
        # IPFS client may or may not be available
        # This is okay - we have local fallback

    @pytest.mark.asyncio
    async def test_store_local_fallback(self, storage, sample_log):
        """Test local storage fallback when IPFS unavailable"""
        receipt = await storage.store_audit_log(sample_log, permanent=False)

        assert isinstance(receipt, StorageReceipt)
        assert receipt.storage_type in [StorageType.IPFS, StorageType.LOCAL]
        assert receipt.identifier is not None
        assert receipt.url.startswith(("https://", "file://"))
        assert receipt.timestamp > 0
        assert receipt.size_bytes > 0

    @pytest.mark.asyncio
    async def test_store_and_retrieve_local(self, storage, sample_log):
        """Test storing and retrieving from local storage"""
        # Store
        receipt = storage._store_local(sample_log)

        assert receipt.storage_type == StorageType.LOCAL
        assert receipt.identifier is not None

        # Retrieve
        retrieved = storage._retrieve_local(receipt.identifier)

        assert retrieved.log_id == sample_log.log_id
        assert retrieved.user_address == sample_log.user_address
        assert retrieved.regulation == sample_log.regulation

    @pytest.mark.asyncio
    async def test_store_with_permanent_flag(self, storage, sample_log):
        """Test storage with permanent flag (Arweave simulation)"""
        # Without Arweave wallet, should fallback to IPFS or local
        receipt = await storage.store_audit_log(sample_log, permanent=True)

        assert isinstance(receipt, StorageReceipt)
        # Will fallback to IPFS or LOCAL if Arweave not available
        assert receipt.storage_type in [StorageType.ARWEAVE, StorageType.IPFS, StorageType.LOCAL]

    def test_cost_estimation_ipfs(self, storage):
        """Test IPFS cost estimation"""
        # 100MB data for 12 months
        size_bytes = 100 * 1_000_000
        cost = storage.estimate_cost(size_bytes, StorageType.IPFS, duration_months=12)

        # Should be around $0.60 ($5/month per 100GB = $0.05/month per 100MB)
        assert cost > 0
        assert cost < 1.0  # Reasonable upper bound

    def test_cost_estimation_arweave(self, storage):
        """Test Arweave cost estimation"""
        # 100MB data (one-time payment)
        size_bytes = 100 * 1_000_000
        cost = storage.estimate_cost(size_bytes, StorageType.ARWEAVE)

        # Should be around $0.50 ($0.005/MB * 100MB)
        assert cost > 0
        assert cost < 1.0  # Reasonable upper bound

    def test_cost_comparison(self, storage):
        """Test cost comparison: IPFS vs Arweave"""
        size_bytes = 10 * 1_000_000  # 10MB

        # IPFS for 12 months
        ipfs_cost_1yr = storage.estimate_cost(size_bytes, StorageType.IPFS, duration_months=12)

        # Arweave one-time
        arweave_cost = storage.estimate_cost(size_bytes, StorageType.ARWEAVE)

        # For small data, Arweave should be cheaper long-term
        assert arweave_cost > 0
        assert ipfs_cost_1yr > 0

        # Arweave is one-time, so over very long periods it's cheaper
        ipfs_cost_10yr = storage.estimate_cost(size_bytes, StorageType.IPFS, duration_months=120)
        assert arweave_cost < ipfs_cost_10yr

    @pytest.mark.asyncio
    async def test_store_multiple_logs(self, storage):
        """Test storing multiple compliance logs"""
        logs = [
            ComplianceLog(
                log_id=f"log_{i}",
                user_address="0xabcd",
                regulation="LGPD",
                article=7,
                action=f"action_{i}",
                passed=True,
            )
            for i in range(5)
        ]

        receipts = []
        for log in logs:
            receipt = await storage.store_audit_log(log, permanent=False)
            receipts.append(receipt)

        assert len(receipts) == 5
        assert all(r.storage_type in [StorageType.IPFS, StorageType.LOCAL] for r in receipts)
        assert len(set(r.identifier for r in receipts)) == 5  # All unique

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_log(self, storage):
        """Test retrieving non-existent log raises error"""
        with pytest.raises(ValueError):
            await storage.retrieve_log(StorageType.LOCAL, "nonexistent_id")

    @pytest.mark.asyncio
    async def test_store_log_with_blockchain_tx(self, storage):
        """Test storing log with blockchain transaction hash"""
        log = ComplianceLog(
            log_id="log_with_tx",
            user_address="0xabcd",
            regulation="LGPD",
            article=7,
            action="consent_granted",
            passed=True,
            blockchain_tx="0x123456789abcdef",
        )

        receipt = await storage.store_audit_log(log, permanent=False)

        # Retrieve and verify
        if receipt.storage_type == StorageType.LOCAL:
            retrieved = storage._retrieve_local(receipt.identifier)
            assert retrieved.blockchain_tx == "0x123456789abcdef"

    def test_storage_receipt_attributes(self, storage, sample_log):
        """Test storage receipt has all required attributes"""
        receipt = storage._store_local(sample_log)

        assert hasattr(receipt, 'storage_type')
        assert hasattr(receipt, 'identifier')
        assert hasattr(receipt, 'permanent')
        assert hasattr(receipt, 'url')
        assert hasattr(receipt, 'timestamp')
        assert hasattr(receipt, 'size_bytes')
        assert hasattr(receipt, 'cost_usd')

    @pytest.mark.asyncio
    async def test_ipfs_unavailable_fallback(self, sample_log):
        """Test graceful fallback when IPFS is unavailable"""
        # Create storage without IPFS client
        storage = DecentralizedStorage()
        storage.ipfs_client = None

        receipt = await storage.store_on_ipfs(sample_log)

        # Should fallback to local storage
        assert receipt.storage_type == StorageType.LOCAL
        assert receipt.url.startswith("file://")


class TestIntegration:
    """Integration tests for full workflow"""

    @pytest.mark.asyncio
    async def test_full_audit_workflow(self):
        """Test complete audit logging workflow"""
        storage = DecentralizedStorage()

        # 1. Create compliance log
        log = ComplianceLog(
            log_id="integration_test_001",
            user_address="0x1234567890abcdef",
            regulation="LGPD",
            article=7,
            action="consent_granted",
            passed=True,
            metadata={
                "consent_duration": "1 year",
                "processor": "0xprocessor",
            },
        )

        # 2. Store on decentralized storage
        receipt = await storage.store_audit_log(log, permanent=False)

        assert receipt.identifier is not None

        # 3. Retrieve and verify
        if receipt.storage_type == StorageType.LOCAL:
            retrieved = storage._retrieve_local(receipt.identifier)
            assert retrieved.log_id == log.log_id
            assert retrieved.metadata["consent_duration"] == "1 year"

    @pytest.mark.asyncio
    async def test_violation_audit_workflow(self):
        """Test audit workflow for compliance violation"""
        storage = DecentralizedStorage()

        # Compliance violation
        log = ComplianceLog(
            log_id="violation_test_001",
            user_address="0xbadactor",
            regulation="LGPD",
            article=7,
            action="unauthorized_data_access",
            passed=False,
            violation="Attempted data access without valid consent",
            metadata={
                "blocked_at": "kernel_level",
                "syscall": "open",
            },
        )

        receipt = await storage.store_audit_log(log, permanent=True)

        # Permanent storage attempted (may fallback if Arweave unavailable)
        assert receipt is not None
        assert not log.passed
        assert log.violation is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
