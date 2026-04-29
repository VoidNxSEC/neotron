"""
Policy Management API Endpoints

Provides full CRUD for compliance policies.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from neutron.api.auth import AuthPrincipal, Role, get_current_user, require_role
from neutron.api.policy_store import (
    CompliancePolicy,
    PolicyCreateRequest,
    PolicyListResponse,
    PolicyResponse,
    PolicyRuleResponse,
    PolicyStatus,
    PolicyType,
    PolicyUpdateRequest,
    get_policy_store,
)

logger = logging.getLogger("neutron.api.policy_endpoints")

router = APIRouter(prefix="/v1/policies", tags=["policies"])


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def policy_to_response(policy: CompliancePolicy) -> PolicyResponse:
    """Convert CompliancePolicy to PolicyResponse."""
    return PolicyResponse(
        policy_id=policy.policy_id,
        name=policy.name,
        description=policy.description,
        policy_type=policy.policy_type.value,
        version=policy.version,
        status=policy.status.value,
        rules=[
            PolicyRuleResponse(
                rule_id=rule.rule_id,
                name=rule.name,
                description=rule.description,
                condition=rule.condition,
                action=rule.action.value,
                error_message=rule.error_message,
            )
            for rule in policy.rules
        ],
        metadata=policy.metadata,
        created_at=policy.created_at,
        created_by=policy.created_by,
        updated_at=policy.updated_at,
        updated_by=policy.updated_by,
        tags=policy.tags,
    )


# ---------------------------------------------------------------------------
# Endpoints - Policy CRUD
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def create_policy(
    request: PolicyCreateRequest,
    principal: AuthPrincipal = Depends(get_current_user),
) -> PolicyResponse:
    """
    Create a new compliance policy (ADMIN only).

    **Example**:
    ```json
    {
      "name": "Custom LGPD Policy for E-commerce",
      "description": "Specific compliance rules for our e-commerce platform",
      "policy_type": "LGPD",
      "rules": [
        {
          "name": "Age Verification",
          "description": "User must be 18+ for purchase",
          "condition": {"field": "age", "operator": ">=", "value": 18},
          "action": "block",
          "error_message": "Must be 18 or older"
        }
      ],
      "tags": ["ecommerce", "lgpd", "age_verification"]
    }
    ```
    """
    policy_store = get_policy_store()

    # Create policy
    policy = policy_store.create_policy(
        name=request.name,
        description=request.description,
        policy_type=request.policy_type,
        rules=request.rules,
        created_by=principal.username,
        metadata=request.metadata,
        tags=request.tags,
    )

    logger.info(f"Policy created: {policy.policy_id} ({policy.name}) by {principal.username}")

    return policy_to_response(policy)


@router.get("", response_model=PolicyListResponse)
async def list_policies(
    policy_type: PolicyType | None = Query(None, description="Filter by policy type"),
    status_filter: PolicyStatus | None = Query(
        None, description="Filter by status", alias="status"
    ),
    tags: str | None = Query(None, description="Comma-separated tags to filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size (max 100)"),
    principal: AuthPrincipal = Depends(get_current_user),
) -> PolicyListResponse:
    """
    List all compliance policies with filters and pagination.

    **Query params**:
    - `policy_type`: Filter by LGPD, GDPR, AI_ACT, HIPAA, CUSTOM
    - `status`: Filter by draft, active, inactive, archived
    - `tags`: Comma-separated tags (e.g., "ecommerce,lgpd")
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 100)

    **Example**: `GET /v1/policies?policy_type=LGPD&status=active&page=1&page_size=20`
    """
    policy_store = get_policy_store()

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    # Get policies
    policies, total = policy_store.list_policies(
        policy_type=policy_type,
        status=status_filter,
        tags=tag_list,
        page=page,
        page_size=page_size,
    )

    return PolicyListResponse(
        policies=[policy_to_response(p) for p in policies],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    principal: AuthPrincipal = Depends(get_current_user),
) -> PolicyResponse:
    """
    Get a specific policy by ID.

    Returns full policy details including all rules.
    """
    policy_store = get_policy_store()

    policy = policy_store.get_policy(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy not found: {policy_id}",
        )

    return policy_to_response(policy)


@router.put(
    "/{policy_id}",
    response_model=PolicyResponse,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def update_policy(
    policy_id: str,
    request: PolicyUpdateRequest,
    principal: AuthPrincipal = Depends(get_current_user),
) -> PolicyResponse:
    """
    Update an existing policy (ADMIN only).

    **Example**:
    ```json
    {
      "name": "Updated Policy Name",
      "status": "active",
      "rules": [
        {
          "name": "New Rule",
          "description": "Updated rule",
          "condition": {"field": "score", "operator": ">", "value": 50},
          "action": "block"
        }
      ]
    }
    ```
    """
    policy_store = get_policy_store()

    # Update policy
    policy = policy_store.update_policy(
        policy_id=policy_id,
        updated_by=principal.username,
        name=request.name,
        description=request.description,
        status=request.status,
        rules=request.rules,
        metadata=request.metadata,
        tags=request.tags,
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy not found: {policy_id}",
        )

    logger.info(f"Policy updated: {policy.policy_id} ({policy.name}) by {principal.username}")

    return policy_to_response(policy)


@router.delete(
    "/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def delete_policy(
    policy_id: str,
    hard_delete: bool = Query(False, description="Permanently delete (use with caution)"),
    principal: AuthPrincipal = Depends(get_current_user),
):
    """
    Delete (archive) a policy (ADMIN only).

    By default, policies are archived (soft delete). Use `?hard_delete=true` to permanently delete.

    **WARNING**: Hard delete is irreversible!
    """
    policy_store = get_policy_store()

    if hard_delete:
        # Hard delete
        success = policy_store.hard_delete_policy(policy_id)
        action = "deleted permanently"
    else:
        # Soft delete (archive)
        success = policy_store.delete_policy(policy_id)
        action = "archived"

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy not found: {policy_id}",
        )

    logger.info(f"Policy {action}: {policy_id} by {principal.username}")

    return None  # 204 No Content


# ---------------------------------------------------------------------------
# Endpoints - Policy Activation
# ---------------------------------------------------------------------------


@router.post(
    "/{policy_id}/activate",
    response_model=PolicyResponse,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def activate_policy(
    policy_id: str,
    principal: AuthPrincipal = Depends(get_current_user),
) -> PolicyResponse:
    """
    Activate a policy (ADMIN only).

    Changes policy status from DRAFT/INACTIVE to ACTIVE.
    """
    policy_store = get_policy_store()

    policy = policy_store.update_policy(
        policy_id=policy_id,
        updated_by=principal.username,
        status=PolicyStatus.ACTIVE,
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy not found: {policy_id}",
        )

    logger.info(f"Policy activated: {policy.policy_id} by {principal.username}")

    return policy_to_response(policy)


@router.post(
    "/{policy_id}/deactivate",
    response_model=PolicyResponse,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def deactivate_policy(
    policy_id: str,
    principal: AuthPrincipal = Depends(get_current_user),
) -> PolicyResponse:
    """
    Deactivate a policy (ADMIN only).

    Changes policy status to INACTIVE (temporarily disabled).
    """
    policy_store = get_policy_store()

    policy = policy_store.update_policy(
        policy_id=policy_id,
        updated_by=principal.username,
        status=PolicyStatus.INACTIVE,
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy not found: {policy_id}",
        )

    logger.info(f"Policy deactivated: {policy.policy_id} by {principal.username}")

    return policy_to_response(policy)
