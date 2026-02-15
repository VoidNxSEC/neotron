"""
Authentication API Endpoints

Provides user authentication, API key management, and token refresh.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from neutron.api.auth import (
    APIKey,
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyInfo,
    APIKeyListResponse,
    AuthPrincipal,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    Role,
    audit_log_auth_event,
    create_access_token,
    get_auth_store,
    get_current_user,
    require_role,
)

logger = logging.getLogger("neutron.api.auth_endpoints")

router = APIRouter(prefix="/v1/auth", tags=["authentication"])


# ---------------------------------------------------------------------------
# Endpoints - Login & Token Management
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """
    Authenticate with username and password.

    Returns access token (JWT, 1h expiry) and refresh token (7d expiry).

    **Example**:
    ```json
    {
      "username": "admin",
      "password": "neutron_admin_2026"
    }
    ```
    """
    auth_store = get_auth_store()

    # Authenticate user
    user = auth_store.authenticate_user(request.username, request.password)
    if not user:
        audit_log_auth_event(
            "login_failed",
            request.username,
            {"reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Create tokens
    access_token, expires_in = create_access_token(user.username, user.role)
    refresh_token = auth_store.create_refresh_token(user.username)

    audit_log_auth_event(
        "login_success",
        user.username,
        {"role": user.role.value, "method": "password"},
    )

    logger.info(f"User logged in: {user.username} (role: {user.role})")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        role=user.role.value,
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(request: RefreshRequest) -> LoginResponse:
    """
    Refresh access token using refresh token.

    Returns new access token and refresh token.
    """
    auth_store = get_auth_store()

    # Verify refresh token
    user_id = auth_store.verify_refresh_token(request.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get user
    user = auth_store.users.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Revoke old refresh token
    auth_store.revoke_refresh_token(request.refresh_token)

    # Create new tokens
    access_token, expires_in = create_access_token(user.username, user.role)
    new_refresh_token = auth_store.create_refresh_token(user.username)

    audit_log_auth_event(
        "token_refresh",
        user.username,
        {"role": user.role.value},
    )

    logger.info(f"Token refreshed for user: {user.username}")

    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
        role=user.role.value,
    )


# ---------------------------------------------------------------------------
# Endpoints - API Key Management
# ---------------------------------------------------------------------------


@router.post("/apikeys", response_model=APIKeyCreateResponse, dependencies=[Depends(require_role(Role.ADMIN))])
async def create_api_key(
    request: APIKeyCreateRequest,
    principal: AuthPrincipal = Depends(get_current_user),
) -> APIKeyCreateResponse:
    """
    Create a new API key (ADMIN only).

    **WARNING**: The API key is only shown once! Save it securely.

    **Example**:
    ```json
    {
      "name": "Production Service",
      "role": "operator"
    }
    ```
    """
    auth_store = get_auth_store()

    # Create API key
    api_key_obj, actual_key = auth_store.create_api_key(
        name=request.name,
        role=request.role,
        created_by=principal.username,
    )

    audit_log_auth_event(
        "apikey_created",
        principal.username,
        {
            "key_id": api_key_obj.key_id,
            "name": request.name,
            "role": request.role.value,
        },
    )

    logger.info(
        f"API key created: {api_key_obj.key_id} ({request.name}) by {principal.username}"
    )

    return APIKeyCreateResponse(
        key_id=api_key_obj.key_id,
        api_key=actual_key,
        name=api_key_obj.name,
        role=api_key_obj.role.value,
        created_at=api_key_obj.created_at,
    )


@router.get("/apikeys", response_model=APIKeyListResponse, dependencies=[Depends(require_role(Role.ADMIN))])
async def list_api_keys(
    include_revoked: bool = False,
    principal: AuthPrincipal = Depends(get_current_user),
) -> APIKeyListResponse:
    """
    List all API keys (ADMIN only).

    Query params:
    - `include_revoked`: Include revoked keys (default: false)
    """
    auth_store = get_auth_store()
    keys = auth_store.list_api_keys(include_revoked=include_revoked)

    return APIKeyListResponse(
        keys=[
            APIKeyInfo(
                key_id=k.key_id,
                name=k.name,
                role=k.role.value,
                created_at=k.created_at,
                created_by=k.created_by,
                last_used=k.last_used,
                revoked=k.revoked,
            )
            for k in keys
        ]
    )


@router.delete("/apikeys/{key_id}", dependencies=[Depends(require_role(Role.ADMIN))])
async def revoke_api_key(
    key_id: str,
    principal: AuthPrincipal = Depends(get_current_user),
) -> dict:
    """
    Revoke an API key (ADMIN only).

    Once revoked, the key cannot be used for authentication.
    """
    auth_store = get_auth_store()

    success = auth_store.revoke_api_key(key_id, revoked_by=principal.username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key not found: {key_id}",
        )

    audit_log_auth_event(
        "apikey_revoked",
        principal.username,
        {"key_id": key_id},
    )

    logger.info(f"API key revoked: {key_id} by {principal.username}")

    return {"status": "revoked", "key_id": key_id, "revoked_by": principal.username}


# ---------------------------------------------------------------------------
# Endpoints - User Info
# ---------------------------------------------------------------------------


@router.get("/me", response_model=AuthPrincipal)
async def get_current_user_info(
    principal: AuthPrincipal = Depends(get_current_user),
) -> AuthPrincipal:
    """
    Get information about the currently authenticated user.

    Returns user ID, role, and authentication method.
    """
    return principal
