"""
Tests for Enterprise Authentication & Authorization
"""

import os

import pytest
from fastapi.testclient import TestClient

# Set API_SECRET_KEY for tests
os.environ["API_SECRET_KEY"] = "test_secret_key_for_neutron_2026"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test_admin_password"

from neutron.api.auth import Role, get_auth_store
from neutron.api.server import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def auth_store():
    """Auth store fixture."""
    return get_auth_store()


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
def operator_user(auth_store):
    """Create an operator user."""
    user = auth_store.create_user(
        username="operator_test",
        password="operator_pass",
        role=Role.OPERATOR,
    )
    return user


@pytest.fixture
def operator_token(client):
    """Get operator access token."""
    # Create operator user first
    store = get_auth_store()
    store.create_user("operator_test", "operator_pass", Role.OPERATOR)

    response = client.post(
        "/v1/auth/login",
        json={"username": "operator_test", "password": "operator_pass"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# Login Tests
# ---------------------------------------------------------------------------


def test_login_success(client):
    """Test successful login."""
    response = client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "test_admin_password"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"
    assert data["expires_in"] > 0


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "wrong_password"},
    )

    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Test login with nonexistent user."""
    response = client.post(
        "/v1/auth/login",
        json={"username": "nonexistent", "password": "password"},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Token Refresh Tests
# ---------------------------------------------------------------------------


def test_token_refresh(client):
    """Test token refresh."""
    # Login first
    login_response = client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "test_admin_password"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh
    refresh_response = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token  # New refresh token


def test_token_refresh_invalid(client):
    """Test token refresh with invalid token."""
    response = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )

    assert response.status_code == 401


def test_token_refresh_reuse_fails(client):
    """Test that refresh token can only be used once."""
    # Login first
    login_response = client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "test_admin_password"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # First refresh - should succeed
    first_refresh = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert first_refresh.status_code == 200

    # Second refresh with same token - should fail
    second_refresh = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert second_refresh.status_code == 401


# ---------------------------------------------------------------------------
# API Key Tests
# ---------------------------------------------------------------------------


def test_create_api_key_admin(client, admin_token):
    """Test API key creation by admin."""
    response = client.post(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Test Service", "role": "operator"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "key_id" in data
    assert "api_key" in data
    assert data["api_key"].startswith("nk_")
    assert data["name"] == "Test Service"
    assert data["role"] == "operator"
    assert "SAVE THIS KEY" in data["warning"]


def test_create_api_key_non_admin_fails(client, operator_token):
    """Test that only admins can create API keys."""
    response = client.post(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"name": "Test Service", "role": "operator"},
    )

    assert response.status_code == 403  # Forbidden


def test_list_api_keys(client, admin_token):
    """Test listing API keys."""
    # Create a key first
    create_response = client.post(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Test Service", "role": "operator"},
    )
    assert create_response.status_code == 200

    # List keys
    list_response = client.get(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert list_response.status_code == 200
    data = list_response.json()
    assert "keys" in data
    assert len(data["keys"]) > 0
    assert data["keys"][0]["name"] == "Test Service"


def test_revoke_api_key(client, admin_token):
    """Test API key revocation."""
    # Create a key
    create_response = client.post(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Test Service", "role": "operator"},
    )
    key_id = create_response.json()["key_id"]

    # Revoke it
    revoke_response = client.delete(
        f"/v1/auth/apikeys/{key_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"

    # List keys with revoked flag
    list_response = client.get(
        "/v1/auth/apikeys?include_revoked=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    keys = list_response.json()["keys"]
    revoked_key = next((k for k in keys if k["key_id"] == key_id), None)
    assert revoked_key is not None
    assert revoked_key["revoked"] is True


def test_authenticate_with_api_key(client, admin_token):
    """Test authentication using API key."""
    # Create an API key
    create_response = client.post(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Test Service", "role": "operator"},
    )
    api_key = create_response.json()["api_key"]

    # Use API key to authenticate
    response = client.get(
        "/v1/auth/me",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["auth_method"] == "apikey"
    assert data["role"] == "operator"
    assert data["username"] == "Test Service"


def test_authenticate_with_revoked_api_key_fails(client, admin_token):
    """Test that revoked API keys cannot authenticate."""
    # Create and revoke a key
    create_response = client.post(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Test Service", "role": "operator"},
    )
    api_key = create_response.json()["api_key"]
    key_id = create_response.json()["key_id"]

    client.delete(
        f"/v1/auth/apikeys/{key_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Try to use revoked key
    response = client.get(
        "/v1/auth/me",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Role-Based Access Control Tests
# ---------------------------------------------------------------------------


def test_admin_can_access_admin_endpoint(client, admin_token):
    """Test that admin can access admin endpoints."""
    response = client.get(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200


def test_operator_cannot_access_admin_endpoint(client, operator_token):
    """Test that operator cannot access admin endpoints."""
    response = client.get(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert response.status_code == 403  # Forbidden


def test_operator_can_access_operator_endpoint(client, operator_token):
    """Test that operator can access operator endpoints."""
    # Compliance validation requires OPERATOR role or higher
    response = client.post(
        "/v1/compliance/validate",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "customer_id": "test_customer",
            "action": "test_action",
            "consent_token": "test_consent",
        },
    )

    # Should not be 403 (might be 500 or other error, but not forbidden)
    assert response.status_code != 403


def test_get_current_user_info(client, admin_token):
    """Test /v1/auth/me endpoint."""
    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert data["auth_method"] == "jwt"


# ---------------------------------------------------------------------------
# Unauthenticated Access Tests
# ---------------------------------------------------------------------------


def test_protected_endpoint_without_auth_fails(client):
    """Test that protected endpoints require authentication."""
    response = client.get("/v1/auth/apikeys")

    assert response.status_code == 401


def test_health_endpoint_no_auth_required(client):
    """Test that health endpoint doesn't require auth."""
    response = client.get("/health")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Multiple Auth Methods Tests
# ---------------------------------------------------------------------------


def test_both_jwt_and_apikey_prioritizes_apikey(client, admin_token):
    """Test that API key takes precedence when both are provided."""
    # Create an operator API key
    create_response = client.post(
        "/v1/auth/apikeys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Test Service", "role": "operator"},
    )
    api_key = create_response.json()["api_key"]

    # Send both JWT (admin) and API key (operator)
    response = client.get(
        "/v1/auth/me",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-API-Key": api_key,
        },
    )

    assert response.status_code == 200
    data = response.json()
    # API key should take precedence
    assert data["auth_method"] == "apikey"
    assert data["role"] == "operator"
