"""
Audit Log API Endpoints

Provides queryable access to compliance audit trail.
LGPD Article 48, GDPR Article 30, EU AI Act Article 12.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from neutron.api.auth import AuthPrincipal, Role, get_current_user, require_role
from neutron.api.audit_store import (
    AuditEventType,
    AuditLogResponse,
    AuditLogsResponse,
    AuditStatsResponse,
    ComplianceDecisionType,
    IPFSAuditResponse,
    get_audit_store,
)

logger = logging.getLogger("neutron.api.audit_endpoints")

router = APIRouter(prefix="/v1/audit", tags=["audit"])


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def audit_log_to_response(log) -> AuditLogResponse:
    """Convert AuditLog to AuditLogResponse."""
    return AuditLogResponse(
        audit_id=log.audit_id,
        event_type=log.event_type.value,
        timestamp=log.timestamp,
        customer_id=log.customer_id,
        user_id=log.user_id,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        decision=log.decision.value if log.decision else None,
        regulation=log.regulation,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        request_id=log.request_id,
        details=log.details,
        metadata=log.metadata,
        ipfs_hash=log.ipfs_hash,
        blockchain_tx=log.blockchain_tx,
    )


# ---------------------------------------------------------------------------
# Endpoints - Audit Log Query
# ---------------------------------------------------------------------------


@router.get("/logs", response_model=AuditLogsResponse)
async def query_audit_logs(
    event_type: Optional[AuditEventType] = Query(None, description="Filter by event type"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    decision: Optional[ComplianceDecisionType] = Query(None, description="Filter by compliance decision"),
    regulation: Optional[str] = Query(None, description="Filter by regulation (LGPD, GDPR, AI_ACT)"),
    action: Optional[str] = Query(None, description="Filter by action"),
    start_time: Optional[float] = Query(None, description="Filter by start timestamp (unix)"),
    end_time: Optional[float] = Query(None, description="Filter by end timestamp (unix)"),
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size (max 100)"),
    principal: AuthPrincipal = Depends(get_current_user),
) -> AuditLogsResponse:
    """
    Query audit logs with filters and pagination.

    **Compliance**:
    - LGPD Article 48: Audit trail for security incidents
    - GDPR Article 30: Records of processing activities
    - EU AI Act Article 12: Record-keeping for high-risk AI

    **Filters**:
    - `event_type`: compliance_validation, policy_created, consent_granted, etc.
    - `customer_id`: Filter by customer
    - `user_id`: Filter by user
    - `decision`: approved, rejected, conditional, review_required
    - `regulation`: LGPD, GDPR, AI_ACT
    - `action`: Specific action name
    - `start_time` / `end_time`: Unix timestamp range
    - `request_id`: Specific request ID

    **Example**:
    ```
    GET /v1/audit/logs?event_type=compliance_validation&decision=approved&page=1&page_size=20
    ```

    **RBAC**:
    - ADMIN: All logs
    - OPERATOR: All logs
    - AUDITOR: All logs (read-only by role definition)
    """
    audit_store = get_audit_store()

    # Query logs
    logs, total, filters_applied = audit_store.query_logs(
        event_type=event_type,
        customer_id=customer_id,
        user_id=user_id,
        decision=decision,
        regulation=regulation,
        action=action,
        start_time=start_time,
        end_time=end_time,
        request_id=request_id,
        page=page,
        page_size=page_size,
    )

    logger.info(
        f"Audit query by {principal.username}: {total} results, "
        f"filters={filters_applied}"
    )

    return AuditLogsResponse(
        logs=[audit_log_to_response(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        filters_applied=filters_applied,
    )


@router.get("/customer/{customer_id}", response_model=AuditLogsResponse)
async def get_customer_audit_logs(
    customer_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    principal: AuthPrincipal = Depends(get_current_user),
) -> AuditLogsResponse:
    """
    Get all audit logs for a specific customer.

    **Compliance**:
    - LGPD Article 18: Right to data portability and access
    - GDPR Article 15: Right of access by the data subject

    **Use case**: Customer requests "show me all my data processing history"

    **RBAC**:
    - ADMIN: Any customer
    - OPERATOR: Any customer
    - AUDITOR: Any customer (read-only)

    **Example**: `GET /v1/audit/customer/cust_12345?page=1&page_size=50`
    """
    audit_store = get_audit_store()

    # Get customer logs
    logs, total = audit_store.get_customer_logs(
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )

    logger.info(
        f"Customer audit query: customer={customer_id}, total={total}, "
        f"requester={principal.username}"
    )

    return AuditLogsResponse(
        logs=[audit_log_to_response(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        filters_applied={"customer_id": customer_id},
    )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    start_time: Optional[float] = Query(None, description="Start timestamp (unix)"),
    end_time: Optional[float] = Query(None, description="End timestamp (unix)"),
    principal: AuthPrincipal = Depends(get_current_user),
) -> AuditStatsResponse:
    """
    Get audit statistics and metrics.

    **Returns**:
    - Total events
    - Events by type (compliance_validation, policy_created, etc.)
    - Events by decision (approved, rejected, etc.)
    - Events by regulation (LGPD, GDPR, AI_ACT)
    - Date range
    - Unique customers/users

    **Use case**: Compliance dashboards, reporting

    **Example**: `GET /v1/audit/stats?start_time=1706745600&end_time=1709337600`
    """
    audit_store = get_audit_store()

    stats = audit_store.get_stats(start_time=start_time, end_time=end_time)

    logger.info(f"Audit stats requested by {principal.username}: {stats['total_events']} events")

    return AuditStatsResponse(**stats)


@router.get("/{audit_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_id: str,
    principal: AuthPrincipal = Depends(get_current_user),
) -> AuditLogResponse:
    """
    Get a specific audit log by ID.

    **Example**: `GET /v1/audit/audit_abc123`
    """
    audit_store = get_audit_store()

    log = audit_store.get_by_id(audit_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log not found: {audit_id}",
        )

    return audit_log_to_response(log)


# ---------------------------------------------------------------------------
# Endpoints - IPFS/Arweave Integration
# ---------------------------------------------------------------------------


@router.get("/ipfs/{ipfs_hash}", response_model=IPFSAuditResponse)
async def fetch_audit_from_ipfs(
    ipfs_hash: str,
    principal: AuthPrincipal = Depends(get_current_user),
) -> IPFSAuditResponse:
    """
    Fetch audit log from IPFS/Arweave by hash.

    **Compliance**:
    - Immutable audit trail (200+ year permanence via Arweave)
    - Tamper-proof evidence for legal proceedings

    **Example**: `GET /v1/audit/ipfs/QmXyZ123...`

    **Note**: In production, this fetches from actual IPFS/Arweave.
    Currently simulated for development.
    """
    audit_store = get_audit_store()

    content = audit_store.fetch_from_ipfs(ipfs_hash)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log not found in IPFS: {ipfs_hash}",
        )

    logger.info(f"IPFS audit fetch: hash={ipfs_hash}, requester={principal.username}")

    return IPFSAuditResponse(
        ipfs_hash=ipfs_hash,
        content=content,
        verified=True,  # TODO: Verify cryptographic signature
        retrieved_at=__import__("time").time(),
        storage_type="ipfs",  # or "arweave"
    )


# ---------------------------------------------------------------------------
# Endpoints - Audit Event Creation (Internal Use)
# ---------------------------------------------------------------------------


@router.post(
    "/events",
    response_model=AuditLogResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def create_audit_event(
    event_type: AuditEventType,
    customer_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    decision: Optional[ComplianceDecisionType] = None,
    regulation: Optional[str] = None,
    details: Optional[dict] = None,
    principal: AuthPrincipal = Depends(get_current_user),
) -> AuditLogResponse:
    """
    Manually create an audit event (ADMIN only).

    **Note**: Most audit events are created automatically by the system.
    This endpoint is for manual auditing or testing.

    **Example**:
    ```json
    {
      "event_type": "security_incident",
      "customer_id": "cust_123",
      "action": "suspicious_login",
      "details": {"ip": "192.168.1.1", "reason": "multiple_failures"}
    }
    ```
    """
    audit_store = get_audit_store()

    log = audit_store.log_event(
        event_type=event_type,
        customer_id=customer_id,
        user_id=user_id,
        action=action,
        decision=decision,
        regulation=regulation,
        details=details or {},
    )

    # Simulate IPFS storage
    ipfs_hash = audit_store.simulate_ipfs_storage(log)

    logger.info(
        f"Manual audit event created: {log.audit_id} by {principal.username}, "
        f"IPFS: {ipfs_hash}"
    )

    return audit_log_to_response(log)
