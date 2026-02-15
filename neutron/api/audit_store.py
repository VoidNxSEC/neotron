"""
Audit Log Store - Queryable Compliance Audit Trail

LGPD Article 48: Security incident records must be kept for 6 months minimum.
GDPR Article 30: Records of processing activities.
EU AI Act Article 12: Record-keeping for high-risk AI systems.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AuditEventType(str, Enum):
    """Types of audit events."""

    COMPLIANCE_VALIDATION = "compliance_validation"
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    POLICY_DELETED = "policy_deleted"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    DATA_ACCESS = "data_access"
    DATA_DELETION = "data_deletion"
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_FAILED = "auth_failed"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    SECURITY_INCIDENT = "security_incident"


class ComplianceDecisionType(str, Enum):
    """Compliance validation decisions."""

    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"
    REVIEW_REQUIRED = "review_required"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class AuditLog:
    """Individual audit log entry."""

    audit_id: str
    event_type: AuditEventType
    timestamp: float
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    decision: Optional[ComplianceDecisionType] = None
    regulation: Optional[str] = None  # LGPD, GDPR, AI_ACT
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ipfs_hash: Optional[str] = None  # For immutable storage
    blockchain_tx: Optional[str] = None  # For blockchain anchoring
    retention_until: Optional[float] = None  # LGPD: min 6 months


# ---------------------------------------------------------------------------
# Pydantic Models (API)
# ---------------------------------------------------------------------------


class AuditLogResponse(BaseModel):
    """Audit log response."""

    audit_id: str
    event_type: str
    timestamp: float
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    decision: Optional[str] = None
    regulation: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ipfs_hash: Optional[str] = None
    blockchain_tx: Optional[str] = None


class AuditLogsResponse(BaseModel):
    """List of audit logs."""

    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class AuditStatsResponse(BaseModel):
    """Audit statistics."""

    total_events: int
    events_by_type: Dict[str, int]
    events_by_decision: Dict[str, int]
    events_by_regulation: Dict[str, int]
    date_range: Dict[str, float]
    unique_customers: int
    unique_users: int


class IPFSAuditResponse(BaseModel):
    """IPFS audit log retrieval."""

    ipfs_hash: str
    content: Dict[str, Any]
    verified: bool
    retrieved_at: float
    storage_type: str  # "ipfs" or "arweave"


# ---------------------------------------------------------------------------
# Audit Store
# ---------------------------------------------------------------------------


class AuditStore:
    """In-memory audit log store (migrate to PostgreSQL in production)."""

    def __init__(self):
        self.logs: List[AuditLog] = []
        self._index_by_customer: Dict[str, List[str]] = {}  # customer_id -> [audit_ids]
        self._index_by_user: Dict[str, List[str]] = {}  # user_id -> [audit_ids]
        self._index_by_request: Dict[str, str] = {}  # request_id -> audit_id

    def log_event(
        self,
        event_type: AuditEventType,
        customer_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        decision: Optional[ComplianceDecisionType] = None,
        regulation: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ipfs_hash: Optional[str] = None,
        blockchain_tx: Optional[str] = None,
    ) -> AuditLog:
        """Log an audit event."""
        audit_id = f"audit_{uuid.uuid4().hex[:16]}"
        timestamp = time.time()

        # LGPD Article 48: Retain for minimum 6 months
        retention_until = timestamp + (6 * 30 * 24 * 60 * 60)  # 6 months

        audit_log = AuditLog(
            audit_id=audit_id,
            event_type=event_type,
            timestamp=timestamp,
            customer_id=customer_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            decision=decision,
            regulation=regulation,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            details=details or {},
            metadata=metadata or {},
            ipfs_hash=ipfs_hash,
            blockchain_tx=blockchain_tx,
            retention_until=retention_until,
        )

        self.logs.append(audit_log)

        # Update indexes
        if customer_id:
            if customer_id not in self._index_by_customer:
                self._index_by_customer[customer_id] = []
            self._index_by_customer[customer_id].append(audit_id)

        if user_id:
            if user_id not in self._index_by_user:
                self._index_by_user[user_id] = []
            self._index_by_user[user_id].append(audit_id)

        if request_id:
            self._index_by_request[request_id] = audit_id

        return audit_log

    def get_by_id(self, audit_id: str) -> Optional[AuditLog]:
        """Get audit log by ID."""
        for log in self.logs:
            if log.audit_id == audit_id:
                return log
        return None

    def get_by_ipfs_hash(self, ipfs_hash: str) -> Optional[AuditLog]:
        """Get audit log by IPFS hash."""
        for log in self.logs:
            if log.ipfs_hash == ipfs_hash:
                return log
        return None

    def query_logs(
        self,
        event_type: Optional[AuditEventType] = None,
        customer_id: Optional[str] = None,
        user_id: Optional[str] = None,
        decision: Optional[ComplianceDecisionType] = None,
        regulation: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        request_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[AuditLog], int, Dict[str, Any]]:
        """
        Query audit logs with filters and pagination.

        Returns: (logs, total, filters_applied)
        """
        filtered = self.logs.copy()
        filters_applied = {}

        # Apply filters
        if event_type:
            filtered = [log for log in filtered if log.event_type == event_type]
            filters_applied["event_type"] = event_type.value

        if customer_id:
            # Use index for performance
            customer_audit_ids = self._index_by_customer.get(customer_id, [])
            filtered = [log for log in filtered if log.audit_id in customer_audit_ids]
            filters_applied["customer_id"] = customer_id

        if user_id:
            # Use index for performance
            user_audit_ids = self._index_by_user.get(user_id, [])
            filtered = [log for log in filtered if log.audit_id in user_audit_ids]
            filters_applied["user_id"] = user_id

        if decision:
            filtered = [log for log in filtered if log.decision == decision]
            filters_applied["decision"] = decision.value

        if regulation:
            filtered = [log for log in filtered if log.regulation == regulation]
            filters_applied["regulation"] = regulation

        if action:
            filtered = [log for log in filtered if log.action == action]
            filters_applied["action"] = action

        if start_time:
            filtered = [log for log in filtered if log.timestamp >= start_time]
            filters_applied["start_time"] = start_time

        if end_time:
            filtered = [log for log in filtered if log.timestamp <= end_time]
            filters_applied["end_time"] = end_time

        if request_id:
            audit_id = self._index_by_request.get(request_id)
            if audit_id:
                filtered = [log for log in filtered if log.audit_id == audit_id]
            else:
                filtered = []
            filters_applied["request_id"] = request_id

        # Sort by timestamp (newest first)
        filtered.sort(key=lambda x: x.timestamp, reverse=True)

        total = len(filtered)

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]

        return paginated, total, filters_applied

    def get_customer_logs(
        self,
        customer_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[AuditLog], int]:
        """Get all audit logs for a specific customer (LGPD Article 18)."""
        customer_audit_ids = self._index_by_customer.get(customer_id, [])
        filtered = [log for log in self.logs if log.audit_id in customer_audit_ids]

        # Sort by timestamp (newest first)
        filtered.sort(key=lambda x: x.timestamp, reverse=True)

        total = len(filtered)

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]

        return paginated, total

    def get_stats(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Get audit statistics."""
        filtered = self.logs

        if start_time:
            filtered = [log for log in filtered if log.timestamp >= start_time]
        if end_time:
            filtered = [log for log in filtered if log.timestamp <= end_time]

        # Count by event type
        events_by_type: Dict[str, int] = {}
        for log in filtered:
            event_type = log.event_type.value
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

        # Count by decision
        events_by_decision: Dict[str, int] = {}
        for log in filtered:
            if log.decision:
                decision = log.decision.value
                events_by_decision[decision] = events_by_decision.get(decision, 0) + 1

        # Count by regulation
        events_by_regulation: Dict[str, int] = {}
        for log in filtered:
            if log.regulation:
                events_by_regulation[log.regulation] = (
                    events_by_regulation.get(log.regulation, 0) + 1
                )

        # Date range
        timestamps = [log.timestamp for log in filtered]
        date_range = {
            "earliest": min(timestamps) if timestamps else None,
            "latest": max(timestamps) if timestamps else None,
        }

        # Unique customers/users
        unique_customers = len({log.customer_id for log in filtered if log.customer_id})
        unique_users = len({log.user_id for log in filtered if log.user_id})

        return {
            "total_events": len(filtered),
            "events_by_type": events_by_type,
            "events_by_decision": events_by_decision,
            "events_by_regulation": events_by_regulation,
            "date_range": date_range,
            "unique_customers": unique_customers,
            "unique_users": unique_users,
        }

    def simulate_ipfs_storage(self, audit_log: AuditLog) -> str:
        """Simulate IPFS storage (generates hash)."""
        # In production, this would upload to IPFS/Arweave
        content = json.dumps(
            {
                "audit_id": audit_log.audit_id,
                "event_type": audit_log.event_type.value,
                "timestamp": audit_log.timestamp,
                "customer_id": audit_log.customer_id,
                "details": audit_log.details,
            },
            sort_keys=True,
        )
        ipfs_hash = f"Qm{hashlib.sha256(content.encode()).hexdigest()[:44]}"
        audit_log.ipfs_hash = ipfs_hash
        return ipfs_hash

    def fetch_from_ipfs(self, ipfs_hash: str) -> Optional[Dict[str, Any]]:
        """Fetch audit log from IPFS (simulated)."""
        # In production, this would fetch from IPFS/Arweave
        log = self.get_by_ipfs_hash(ipfs_hash)
        if not log:
            return None

        return {
            "audit_id": log.audit_id,
            "event_type": log.event_type.value,
            "timestamp": log.timestamp,
            "customer_id": log.customer_id,
            "user_id": log.user_id,
            "action": log.action,
            "decision": log.decision.value if log.decision else None,
            "regulation": log.regulation,
            "details": log.details,
            "metadata": log.metadata,
            "ipfs_hash": log.ipfs_hash,
            "blockchain_tx": log.blockchain_tx,
        }


# Global store instance
_audit_store = AuditStore()


def get_audit_store() -> AuditStore:
    """Get the global audit store."""
    return _audit_store
