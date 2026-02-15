"""
Tests for Audit Log API
"""

import os
import time
import pytest
from fastapi.testclient import TestClient

# Set API_SECRET_KEY for tests
os.environ["API_SECRET_KEY"] = "test_secret_key_for_neutron_2026"
os.environ["ADMIN_PASSWORD"] = "test_admin_password"

from neutron.api.server import app
from neutron.api.audit_store import AuditEventType, ComplianceDecisionType, get_audit_store


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def audit_store():
    """Audit store fixture."""
    store = get_audit_store()
    # Clear logs for each test
    store.logs.clear()
    store._index_by_customer.clear()
    store._index_by_user.clear()
    store._index_by_request.clear()
    return store


@pytest.fixture
def admin_token(client):
    """Get admin access token."""
    response = client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "test_admin_password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def sample_audit_logs(audit_store):
    """Create sample audit logs for testing."""
    logs = []

    # Create compliance validation logs
    for i in range(10):
        log = audit_store.log_event(
            event_type=AuditEventType.COMPLIANCE_VALIDATION,
            customer_id=f"customer_{i % 3}",  # 3 different customers
            user_id=f"user_{i % 2}",  # 2 different users
            action="loan_approval",
            decision=ComplianceDecisionType.APPROVED if i % 2 == 0 else ComplianceDecisionType.REJECTED,
            regulation="LGPD",
            request_id=f"req_{i}",
            details={"amount": 1000 * (i + 1)},
        )
        logs.append(log)

    # Create policy events
    for i in range(5):
        log = audit_store.log_event(
            event_type=AuditEventType.POLICY_CREATED,
            user_id="admin",
            resource_type="policy",
            resource_id=f"policy_{i}",
            details={"policy_name": f"Policy {i}"},
        )
        logs.append(log)

    return logs


# ---------------------------------------------------------------------------
# Audit Log Query Tests
# ---------------------------------------------------------------------------


def test_query_all_logs(client, admin_token, sample_audit_logs):
    """Test querying all audit logs."""
    response = client.get(
        "/v1/audit/logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "total" in data
    assert data["total"] == 15  # 10 compliance + 5 policy
    assert len(data["logs"]) <= 15


def test_query_logs_filter_by_event_type(client, admin_token, sample_audit_logs):
    """Test filtering by event type."""
    response = client.get(
        "/v1/audit/logs?event_type=compliance_validation",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 10
    assert all(log["event_type"] == "compliance_validation" for log in data["logs"])


def test_query_logs_filter_by_customer(client, admin_token, sample_audit_logs):
    """Test filtering by customer ID."""
    response = client.get(
        "/v1/audit/logs?customer_id=customer_0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(log["customer_id"] == "customer_0" for log in data["logs"])


def test_query_logs_filter_by_decision(client, admin_token, sample_audit_logs):
    """Test filtering by compliance decision."""
    response = client.get(
        "/v1/audit/logs?decision=approved",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(log["decision"] == "approved" for log in data["logs"] if log["decision"])


def test_query_logs_filter_by_regulation(client, admin_token, sample_audit_logs):
    """Test filtering by regulation."""
    response = client.get(
        "/v1/audit/logs?regulation=LGPD",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(log["regulation"] == "LGPD" for log in data["logs"] if log["regulation"])


def test_query_logs_pagination(client, admin_token, sample_audit_logs):
    """Test pagination."""
    # Page 1
    response1 = client.get(
        "/v1/audit/logs?page=1&page_size=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["logs"]) == 5
    assert data1["page"] == 1
    assert data1["total"] == 15

    # Page 2
    response2 = client.get(
        "/v1/audit/logs?page=2&page_size=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["logs"]) == 5
    assert data2["page"] == 2

    # Logs should be different
    log_ids_1 = {log["audit_id"] for log in data1["logs"]}
    log_ids_2 = {log["audit_id"] for log in data2["logs"]}
    assert log_ids_1.isdisjoint(log_ids_2)


def test_query_logs_time_range(client, admin_token, audit_store):
    """Test filtering by time range."""
    # Create logs with different timestamps
    now = time.time()

    audit_store.log_event(
        event_type=AuditEventType.COMPLIANCE_VALIDATION,
        customer_id="test",
    )

    # Create a log "in the past"
    past_log = audit_store.log_event(
        event_type=AuditEventType.POLICY_CREATED,
        user_id="admin",
    )
    past_log.timestamp = now - 3600  # 1 hour ago

    # Query recent logs only
    response = client.get(
        f"/v1/audit/logs?start_time={now - 60}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1  # Only the recent log


def test_query_logs_multiple_filters(client, admin_token, sample_audit_logs):
    """Test combining multiple filters."""
    response = client.get(
        "/v1/audit/logs?event_type=compliance_validation&decision=approved&regulation=LGPD",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(
        log["event_type"] == "compliance_validation" and
        log["decision"] == "approved" and
        log["regulation"] == "LGPD"
        for log in data["logs"]
    )


# ---------------------------------------------------------------------------
# Customer Audit Logs Tests (LGPD Article 18)
# ---------------------------------------------------------------------------


def test_get_customer_logs(client, admin_token, sample_audit_logs):
    """Test getting all logs for a specific customer."""
    response = client.get(
        "/v1/audit/customer/customer_0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(log["customer_id"] == "customer_0" for log in data["logs"])
    assert data["total"] > 0


def test_get_customer_logs_pagination(client, admin_token, audit_store):
    """Test customer logs pagination."""
    # Create many logs for one customer
    for i in range(20):
        audit_store.log_event(
            event_type=AuditEventType.COMPLIANCE_VALIDATION,
            customer_id="customer_many_logs",
            action=f"action_{i}",
        )

    response = client.get(
        "/v1/audit/customer/customer_many_logs?page=1&page_size=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) == 10
    assert data["total"] == 20


def test_get_customer_logs_nonexistent(client, admin_token):
    """Test getting logs for nonexistent customer."""
    response = client.get(
        "/v1/audit/customer/nonexistent_customer",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["logs"]) == 0


# ---------------------------------------------------------------------------
# Audit Statistics Tests
# ---------------------------------------------------------------------------


def test_get_audit_stats(client, admin_token, sample_audit_logs):
    """Test getting audit statistics."""
    response = client.get(
        "/v1/audit/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "events_by_type" in data
    assert "events_by_decision" in data
    assert "events_by_regulation" in data
    assert "date_range" in data
    assert "unique_customers" in data
    assert "unique_users" in data

    assert data["total_events"] == 15
    assert data["events_by_type"]["compliance_validation"] == 10
    assert data["events_by_type"]["policy_created"] == 5
    assert data["unique_customers"] == 3
    assert data["unique_users"] == 3  # 2 from compliance + 1 admin


def test_get_audit_stats_time_range(client, admin_token, audit_store):
    """Test audit stats with time range."""
    now = time.time()

    # Create recent log
    audit_store.log_event(
        event_type=AuditEventType.COMPLIANCE_VALIDATION,
        customer_id="test",
    )

    # Create old log
    old_log = audit_store.log_event(
        event_type=AuditEventType.POLICY_CREATED,
        user_id="admin",
    )
    old_log.timestamp = now - 7200  # 2 hours ago

    # Get stats for last hour
    response = client.get(
        f"/v1/audit/stats?start_time={now - 3600}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 1


# ---------------------------------------------------------------------------
# Get Specific Audit Log Tests
# ---------------------------------------------------------------------------


def test_get_audit_log_by_id(client, admin_token, audit_store):
    """Test getting a specific audit log."""
    # Create a log
    log = audit_store.log_event(
        event_type=AuditEventType.COMPLIANCE_VALIDATION,
        customer_id="test_customer",
        decision=ComplianceDecisionType.APPROVED,
        details={"test": "data"},
    )

    # Get it
    response = client.get(
        f"/v1/audit/{log.audit_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["audit_id"] == log.audit_id
    assert data["customer_id"] == "test_customer"
    assert data["decision"] == "approved"
    assert data["details"]["test"] == "data"


def test_get_nonexistent_audit_log(client, admin_token):
    """Test getting a nonexistent audit log."""
    response = client.get(
        "/v1/audit/nonexistent_audit_id",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# IPFS Integration Tests
# ---------------------------------------------------------------------------


def test_fetch_from_ipfs(client, admin_token, audit_store):
    """Test fetching audit log from IPFS."""
    # Create a log and store in IPFS
    log = audit_store.log_event(
        event_type=AuditEventType.COMPLIANCE_VALIDATION,
        customer_id="test",
        decision=ComplianceDecisionType.APPROVED,
    )
    ipfs_hash = audit_store.simulate_ipfs_storage(log)

    # Fetch from IPFS
    response = client.get(
        f"/v1/audit/ipfs/{ipfs_hash}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ipfs_hash"] == ipfs_hash
    assert "content" in data
    assert data["content"]["audit_id"] == log.audit_id
    assert data["verified"] is True
    assert data["storage_type"] == "ipfs"


def test_fetch_from_ipfs_nonexistent(client, admin_token):
    """Test fetching nonexistent IPFS hash."""
    response = client.get(
        "/v1/audit/ipfs/Qm_nonexistent_hash",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Manual Event Creation Tests
# ---------------------------------------------------------------------------


def test_create_audit_event_admin(client, admin_token):
    """Test manually creating an audit event (ADMIN only)."""
    response = client.post(
        "/v1/audit/events?event_type=security_incident&customer_id=test&action=suspicious_login",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["event_type"] == "security_incident"
    assert data["customer_id"] == "test"
    assert data["action"] == "suspicious_login"
    assert "audit_id" in data
    assert data["ipfs_hash"] is not None


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------


def test_query_logs_without_auth(client):
    """Test that querying logs requires authentication."""
    response = client.get("/v1/audit/logs")
    assert response.status_code == 401


def test_customer_logs_without_auth(client):
    """Test that customer logs require authentication."""
    response = client.get("/v1/audit/customer/test")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Filters Applied Metadata Test
# ---------------------------------------------------------------------------


def test_filters_applied_metadata(client, admin_token, sample_audit_logs):
    """Test that filters_applied is returned correctly."""
    response = client.get(
        "/v1/audit/logs?event_type=compliance_validation&regulation=LGPD&decision=approved",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "filters_applied" in data
    assert data["filters_applied"]["event_type"] == "compliance_validation"
    assert data["filters_applied"]["regulation"] == "LGPD"
    assert data["filters_applied"]["decision"] == "approved"
