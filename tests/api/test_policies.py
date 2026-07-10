"""
Tests for Policy Management API
"""

import os

import pytest
from fastapi.testclient import TestClient

# Set API_SECRET_KEY for tests
os.environ["API_SECRET_KEY"] = "test_secret_key_for_neutron_2026"
os.environ["ADMIN_PASSWORD"] = "test_admin_password"

from neutron.api.policy_store import get_policy_store
from neutron.api.server import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


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
    # Create operator user first
    from neutron.api.auth import Role, get_auth_store

    store = get_auth_store()
    try:
        store.create_user("operator_test", "operator_pass", Role.OPERATOR)
    except ValueError:
        pass

    response = client.post(
        "/v1/auth/login",
        json={"username": "operator_test", "password": "operator_pass"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# Policy Creation Tests
# ---------------------------------------------------------------------------


def test_create_policy_admin(client, admin_token):
    """Test policy creation by admin."""
    response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Test E-commerce Policy",
            "description": "Custom policy for e-commerce compliance",
            "policy_type": "LGPD",
            "rules": [
                {
                    "name": "Age Verification",
                    "description": "User must be 18+",
                    "condition": {"field": "age", "operator": ">=", "value": 18},
                    "action": "block",
                    "error_message": "Must be 18 or older",
                }
            ],
            "tags": ["ecommerce", "age_check"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test E-commerce Policy"
    assert data["policy_type"] == "LGPD"
    assert data["status"] == "draft"  # New policies start as draft
    assert len(data["rules"]) == 1
    assert data["rules"][0]["name"] == "Age Verification"
    assert data["tags"] == ["ecommerce", "age_check"]
    assert "policy_id" in data
    assert data["policy_id"].startswith("policy_")


def test_create_policy_non_admin_fails(client, operator_token):
    """Test that only admins can create policies."""
    response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "name": "Test Policy",
            "description": "This should fail",
            "policy_type": "LGPD",
            "rules": [],
        },
    )

    assert response.status_code == 403  # Forbidden


def test_create_policy_without_auth_fails(client):
    """Test that policy creation requires authentication."""
    response = client.post(
        "/v1/policies",
        json={
            "name": "Test Policy",
            "description": "This should fail",
            "policy_type": "LGPD",
            "rules": [],
        },
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Policy Listing Tests
# ---------------------------------------------------------------------------


def test_list_policies(client, admin_token):
    """Test listing all policies."""
    response = client.get(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "policies" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["total"] >= 3  # At least 3 default policies (LGPD, GDPR, AI Act)


def test_list_policies_filter_by_type(client, admin_token):
    """Test filtering policies by type."""
    response = client.get(
        "/v1/policies?policy_type=LGPD",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(p["policy_type"] == "LGPD" for p in data["policies"])


def test_list_policies_filter_by_status(client, admin_token):
    """Test filtering policies by status."""
    response = client.get(
        "/v1/policies?status=active",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(p["status"] == "active" for p in data["policies"])


def test_list_policies_pagination(client, admin_token):
    """Test policy pagination."""
    # Create several policies first
    for i in range(5):
        client.post(
            "/v1/policies",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"Test Policy {i}",
                "description": f"Policy number {i}",
                "policy_type": "CUSTOM",
                "rules": [],
            },
        )

    # Get page 1 with page_size=3
    response = client.get(
        "/v1/policies?page=1&page_size=3",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["policies"]) <= 3
    assert data["page"] == 1
    assert data["page_size"] == 3


# ---------------------------------------------------------------------------
# Policy Retrieval Tests
# ---------------------------------------------------------------------------


def test_get_policy(client, admin_token):
    """Test getting a specific policy."""
    # Create a policy first
    create_response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Test Policy",
            "description": "Test description",
            "policy_type": "LGPD",
            "rules": [],
        },
    )
    policy_id = create_response.json()["policy_id"]

    # Get the policy
    response = client.get(
        f"/v1/policies/{policy_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["policy_id"] == policy_id
    assert data["name"] == "Test Policy"


def test_get_nonexistent_policy(client, admin_token):
    """Test getting a policy that doesn't exist."""
    response = client.get(
        "/v1/policies/nonexistent_policy",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Policy Update Tests
# ---------------------------------------------------------------------------


def test_update_policy_admin(client, admin_token):
    """Test updating a policy."""
    # Create a policy first
    create_response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Original Name",
            "description": "Original description",
            "policy_type": "LGPD",
            "rules": [],
        },
    )
    policy_id = create_response.json()["policy_id"]

    # Update the policy
    update_response = client.put(
        f"/v1/policies/{policy_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Updated Name",
            "description": "Updated description",
            "status": "active",
        },
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"
    assert data["status"] == "active"
    assert data["updated_at"] is not None


def test_update_policy_non_admin_fails(client, operator_token):
    """Test that only admins can update policies."""
    # Get a default policy ID

    store = get_policy_store()
    policy_id = "policy_lgpd_default"

    response = client.put(
        f"/v1/policies/{policy_id}",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"name": "This should fail"},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Policy Deletion Tests
# ---------------------------------------------------------------------------


def test_delete_policy_soft(client, admin_token):
    """Test soft deleting (archiving) a policy."""
    # Create a policy first
    create_response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Policy to Delete",
            "description": "Will be archived",
            "policy_type": "CUSTOM",
            "rules": [],
        },
    )
    policy_id = create_response.json()["policy_id"]

    # Delete (archive) the policy
    delete_response = client.delete(
        f"/v1/policies/{policy_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert delete_response.status_code == 204

    # Verify it's archived
    get_response = client.get(
        f"/v1/policies/{policy_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "archived"


def test_delete_policy_hard(client, admin_token):
    """Test hard deleting (permanent) a policy."""
    # Create a policy first
    create_response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Policy to Delete",
            "description": "Will be permanently deleted",
            "policy_type": "CUSTOM",
            "rules": [],
        },
    )
    policy_id = create_response.json()["policy_id"]

    # Hard delete the policy
    delete_response = client.delete(
        f"/v1/policies/{policy_id}?hard_delete=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert delete_response.status_code == 204

    # Verify it's gone
    get_response = client.get(
        f"/v1/policies/{policy_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 404


# ---------------------------------------------------------------------------
# Policy Activation Tests
# ---------------------------------------------------------------------------


def test_activate_policy(client, admin_token):
    """Test activating a policy."""
    # Create a draft policy
    create_response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Draft Policy",
            "description": "Will be activated",
            "policy_type": "LGPD",
            "rules": [],
        },
    )
    policy_id = create_response.json()["policy_id"]

    # Activate it
    activate_response = client.post(
        f"/v1/policies/{policy_id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert activate_response.status_code == 200
    data = activate_response.json()
    assert data["status"] == "active"


def test_deactivate_policy(client, admin_token):
    """Test deactivating a policy."""
    # Create and activate a policy
    create_response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Active Policy",
            "description": "Will be deactivated",
            "policy_type": "LGPD",
            "rules": [],
        },
    )
    policy_id = create_response.json()["policy_id"]

    client.post(
        f"/v1/policies/{policy_id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Deactivate it
    deactivate_response = client.post(
        f"/v1/policies/{policy_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert deactivate_response.status_code == 200
    data = deactivate_response.json()
    assert data["status"] == "inactive"


# ---------------------------------------------------------------------------
# Policy Rules Tests
# ---------------------------------------------------------------------------


def test_policy_with_multiple_rules(client, admin_token):
    """Test creating a policy with multiple rules."""
    response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Multi-Rule Policy",
            "description": "Policy with multiple rules",
            "policy_type": "LGPD",
            "rules": [
                {
                    "name": "Rule 1",
                    "description": "First rule",
                    "condition": {"field": "age", "operator": ">=", "value": 18},
                    "action": "block",
                },
                {
                    "name": "Rule 2",
                    "description": "Second rule",
                    "condition": {"field": "consent", "operator": "exists"},
                    "action": "warn",
                },
                {
                    "name": "Rule 3",
                    "description": "Third rule",
                    "condition": {"field": "country", "operator": "==", "value": "BR"},
                    "action": "audit",
                },
            ],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["rules"]) == 3
    assert data["rules"][0]["name"] == "Rule 1"
    assert data["rules"][1]["name"] == "Rule 2"
    assert data["rules"][2]["name"] == "Rule 3"


def test_update_policy_rules(client, admin_token):
    """Test updating policy rules."""
    # Create a policy with one rule
    create_response = client.post(
        "/v1/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Policy with Rules",
            "description": "Will update rules",
            "policy_type": "CUSTOM",
            "rules": [
                {
                    "name": "Original Rule",
                    "description": "Original",
                    "condition": {"field": "x", "operator": "==", "value": 1},
                    "action": "block",
                }
            ],
        },
    )
    policy_id = create_response.json()["policy_id"]

    # Update with different rules
    update_response = client.put(
        f"/v1/policies/{policy_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "rules": [
                {
                    "name": "New Rule 1",
                    "description": "First new rule",
                    "condition": {"field": "y", "operator": ">", "value": 10},
                    "action": "warn",
                },
                {
                    "name": "New Rule 2",
                    "description": "Second new rule",
                    "condition": {"field": "z", "operator": "<", "value": 5},
                    "action": "audit",
                },
            ]
        },
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert len(data["rules"]) == 2
    assert data["rules"][0]["name"] == "New Rule 1"
    assert data["rules"][1]["name"] == "New Rule 2"
