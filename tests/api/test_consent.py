"""
Tests for Consent Management API
"""

import os
import time

import pytest
from fastapi.testclient import TestClient

# Set API_SECRET_KEY for tests
os.environ["API_SECRET_KEY"] = "test_secret_key_for_neutron_2026"
os.environ["ADMIN_PASSWORD"] = "test_admin_password"

from neutron.api.auth import Role, get_auth_store
from neutron.api.consent_store import get_consent_store
from neutron.api.server import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def consent_store():
    """Consent store fixture."""
    store = get_consent_store()
    # Clear for each test
    store.consents.clear()
    store._index_by_customer.clear()
    store._token_hash_to_id.clear()
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
def operator_token(client):
    """Get operator access token."""
    auth_store = get_auth_store()
    auth_store.create_user("operator_test", "operator_pass", Role.OPERATOR)

    response = client.post(
        "/v1/auth/login",
        json={"username": "operator_test", "password": "operator_pass"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# Consent Creation Tests
# ---------------------------------------------------------------------------


def test_create_consent_operator(client, operator_token):
    """Test consent creation by operator."""
    response = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_br_123",
            "regulation": "LGPD",
            "purposes": ["marketing", "analytics"],
            "data_types": ["email", "phone"],
            "expires_in_days": 365,
            "metadata": {"consent_method": "web_form"},
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == "customer_br_123"
    assert data["regulation"] == "LGPD"
    assert "marketing" in data["purposes"]
    assert "email" in data["data_types"]
    assert data["status"] == "active"
    assert data["version"] == 1
    assert "consent_token" in data
    assert data["consent_token"].startswith("consent_")
    assert "SAVE THIS TOKEN" in data["warning"]


def test_create_consent_without_expiry(client, operator_token):
    """Test creating consent without expiry."""
    response = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_123",
            "regulation": "LGPD",
            "purposes": ["service_improvement"],
            "data_types": ["browsing_history"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["expires_at"] is None  # No expiry


def test_create_consent_versioning(client, operator_token):
    """Test consent versioning (new consent supersedes old)."""
    # Create first consent
    response1 = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_versioning",
            "regulation": "LGPD",
            "purposes": ["marketing"],
            "data_types": ["email"],
        },
    )
    assert response1.status_code == 201
    assert response1.json()["version"] == 1

    # Create second consent (should supersede first)
    response2 = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_versioning",
            "regulation": "LGPD",
            "purposes": ["marketing", "analytics"],
            "data_types": ["email", "phone"],
        },
    )
    assert response2.status_code == 201
    assert response2.json()["version"] == 2

    # Check first consent is superseded
    token_id_1 = response1.json()["token_id"]
    get_response = client.get(
        f"/v1/consent/tokens/{token_id_1}",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert get_response.json()["status"] == "superseded"


# ---------------------------------------------------------------------------
# Consent Verification Tests
# ---------------------------------------------------------------------------


def test_verify_valid_consent(client, operator_token):
    """Test verifying a valid consent token."""
    # Create consent
    create_response = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_verify",
            "regulation": "LGPD",
            "purposes": ["marketing"],
            "data_types": ["email"],
        },
    )
    consent_token = create_response.json()["consent_token"]

    # Verify it
    verify_response = client.post(
        f"/v1/consent/verify?consent_token={consent_token}",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert verify_response.status_code == 200
    data = verify_response.json()
    assert data["valid"] is True
    assert data["customer_id"] == "customer_verify"
    assert data["status"] == "active"
    assert "marketing" in data["purposes"]


def test_verify_revoked_consent(client, operator_token):
    """Test verifying a revoked consent."""
    # Create and revoke consent
    create_response = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_revoke",
            "regulation": "LGPD",
            "purposes": ["marketing"],
            "data_types": ["email"],
        },
    )
    consent_token = create_response.json()["consent_token"]
    token_id = create_response.json()["token_id"]

    # Revoke it
    client.delete(
        f"/v1/consent/tokens/{token_id}",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"reason": "User requested"},
    )

    # Try to verify
    verify_response = client.post(
        f"/v1/consent/verify?consent_token={consent_token}",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert verify_response.status_code == 200
    data = verify_response.json()
    assert data["valid"] is False
    assert data["status"] == "revoked"
    assert "revoked" in data["reason"].lower()


def test_verify_expired_consent(client, operator_token, consent_store):
    """Test verifying an expired consent."""
    # Create consent with short expiry
    consent, actual_token = consent_store.create_consent(
        customer_id="customer_expire",
        regulation="LGPD",
        purposes=[],
        data_types=[],
        expires_in_days=1,
    )

    # Manually expire it
    consent.expires_at = time.time() - 1

    # Try to verify
    verify_response = client.post(
        f"/v1/consent/verify?consent_token={actual_token}",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert verify_response.status_code == 200
    data = verify_response.json()
    assert data["valid"] is False
    assert "expired" in data["reason"].lower()


def test_verify_invalid_token(client, operator_token):
    """Test verifying an invalid token."""
    response = client.post(
        "/v1/consent/verify?consent_token=invalid_token",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Consent Revocation Tests (LGPD Article 18)
# ---------------------------------------------------------------------------


def test_revoke_consent(client, operator_token):
    """Test revoking a consent token."""
    # Create consent
    create_response = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_revoke_test",
            "regulation": "LGPD",
            "purposes": ["marketing"],
            "data_types": ["email"],
        },
    )
    token_id = create_response.json()["token_id"]

    # Revoke it
    revoke_response = client.delete(
        f"/v1/consent/tokens/{token_id}",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"reason": "User no longer wants marketing emails"},
    )

    assert revoke_response.status_code == 200
    data = revoke_response.json()
    assert data["status"] == "revoked"
    assert data["revoked_reason"] == "User no longer wants marketing emails"
    assert data["revoked_at"] is not None


def test_revoke_nonexistent_consent(client, operator_token):
    """Test revoking nonexistent consent."""
    response = client.delete(
        "/v1/consent/tokens/nonexistent_token",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Customer Consent Listing Tests
# ---------------------------------------------------------------------------


def test_list_customer_consents(client, operator_token):
    """Test listing all consents for a customer."""
    # Create multiple consents
    for i in range(3):
        client.post(
            "/v1/consent/tokens",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={
                "customer_id": "customer_multi",
                "regulation": "LGPD",
                "purposes": ["marketing"],
                "data_types": ["email"],
            },
        )

    # List consents
    response = client.get(
        "/v1/consent/customer/customer_multi",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1  # Only the latest (others superseded)
    assert len(data["consents"]) == 1


def test_list_customer_consents_include_revoked(client, operator_token):
    """Test listing consents including revoked ones."""
    # Create and revoke a consent
    create_response = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_revoked_list",
            "regulation": "LGPD",
            "purposes": ["marketing"],
            "data_types": ["email"],
        },
    )
    token_id = create_response.json()["token_id"]

    client.delete(
        f"/v1/consent/tokens/{token_id}",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    # List without revoked
    response1 = client.get(
        "/v1/consent/customer/customer_revoked_list",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response1.json()["total"] == 0

    # List with revoked
    response2 = client.get(
        "/v1/consent/customer/customer_revoked_list?include_revoked=true",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response2.json()["total"] == 1


def test_list_customer_consents_empty(client, operator_token):
    """Test listing consents for customer with no consents."""
    response = client.get(
        "/v1/consent/customer/customer_no_consents",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# Consent Check Tests
# ---------------------------------------------------------------------------


def test_check_customer_consent_by_purpose(client, operator_token):
    """Test checking if customer has consent for a purpose."""
    # Create consent
    client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_check",
            "regulation": "LGPD",
            "purposes": ["marketing", "analytics"],
            "data_types": ["email"],
        },
    )

    # Check marketing (should have)
    response1 = client.get(
        "/v1/consent/customer/customer_check/check?purpose=marketing",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response1.status_code == 200
    assert response1.json()["has_consent"] is True

    # Check research (should not have)
    response2 = client.get(
        "/v1/consent/customer/customer_check/check?purpose=research",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response2.status_code == 200
    assert response2.json()["has_consent"] is False


def test_check_customer_consent_by_data_type(client, operator_token):
    """Test checking if customer has consent for a data type."""
    # Create consent
    client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_data_check",
            "regulation": "LGPD",
            "purposes": ["marketing"],
            "data_types": ["email", "phone"],
        },
    )

    # Check email (should have)
    response1 = client.get(
        "/v1/consent/customer/customer_data_check/check?data_type=email",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response1.status_code == 200
    assert response1.json()["has_consent"] is True

    # Check address (should not have)
    response2 = client.get(
        "/v1/consent/customer/customer_data_check/check?data_type=address",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response2.status_code == 200
    assert response2.json()["has_consent"] is False


def test_check_consent_missing_params(client, operator_token):
    """Test checking consent without required parameters."""
    response = client.get(
        "/v1/consent/customer/customer_test/check",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert response.status_code == 400  # Must provide purpose or data_type


# ---------------------------------------------------------------------------
# Get Consent by ID Tests
# ---------------------------------------------------------------------------


def test_get_consent_by_id(client, operator_token):
    """Test getting consent details by ID."""
    # Create consent
    create_response = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_get",
            "regulation": "LGPD",
            "purposes": ["marketing"],
            "data_types": ["email"],
        },
    )
    token_id = create_response.json()["token_id"]

    # Get by ID
    response = client.get(
        f"/v1/consent/tokens/{token_id}",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_id"] == token_id
    assert data["customer_id"] == "customer_get"
    assert "consent_token" not in data or data["consent_token"] is None  # Not shown


def test_get_nonexistent_consent(client, operator_token):
    """Test getting nonexistent consent."""
    response = client.get(
        "/v1/consent/tokens/nonexistent_token",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------


def test_create_consent_without_auth(client):
    """Test that creating consent requires authentication."""
    response = client.post(
        "/v1/consent/tokens",
        json={
            "customer_id": "test",
            "regulation": "LGPD",
            "purposes": ["marketing"],
            "data_types": ["email"],
        },
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Granular Permissions Tests
# ---------------------------------------------------------------------------


def test_multiple_purposes(client, operator_token):
    """Test consent with multiple purposes."""
    response = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_multi_purpose",
            "regulation": "LGPD",
            "purposes": ["marketing", "analytics", "personalization"],
            "data_types": ["email"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["purposes"]) == 3
    assert "marketing" in data["purposes"]
    assert "analytics" in data["purposes"]
    assert "personalization" in data["purposes"]


def test_multiple_data_types(client, operator_token):
    """Test consent with multiple data types."""
    response = client.post(
        "/v1/consent/tokens",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "customer_multi_data",
            "regulation": "LGPD",
            "purposes": ["marketing"],
            "data_types": ["email", "phone", "address", "cpf"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["data_types"]) == 4
