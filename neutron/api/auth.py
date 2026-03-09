"""
Enterprise-grade Authentication & Authorization for Neutron API

Features:
- API Key management (create, revoke, list)
- Role-Based Access Control (ADMIN, OPERATOR, AUDITOR)
- JWT token management with refresh
- Audit logging for all auth events
- In-memory store (can migrate to DB later)
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from neutron.core.sops import secret as _sops_secret

logger = logging.getLogger("neutron.api.auth")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Reads from /run/secrets/api_secret_key (sops-nix) → env API_SECRET_KEY → None (open mode)
API_SECRET_KEY: str | None = _sops_secret("api_secret_key") or None
JWT_EXPIRATION_SECONDS: int = int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))  # 1 hour
REFRESH_TOKEN_EXPIRATION_SECONDS: int = int(
    os.getenv("REFRESH_TOKEN_EXPIRATION_SECONDS", "604800")  # 7 days
)

# Default admin credentials (CHANGE IN PRODUCTION!)
DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "neutron_admin_2026")

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Role(str, Enum):
    """User roles with hierarchical permissions."""

    ADMIN = "admin"  # Full access - all operations
    OPERATOR = "operator"  # Validate, query, manage policies
    AUDITOR = "auditor"  # Read-only - audit logs only


# Role hierarchy (higher role includes lower role permissions)
ROLE_HIERARCHY = {
    Role.ADMIN: [Role.ADMIN, Role.OPERATOR, Role.AUDITOR],
    Role.OPERATOR: [Role.OPERATOR, Role.AUDITOR],
    Role.AUDITOR: [Role.AUDITOR],
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class User:
    """User with credentials and role."""

    username: str
    password_hash: str  # SHA256 hash
    role: Role
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None


@dataclass
class APIKey:
    """API Key for service-to-service authentication."""

    key_id: str
    key_hash: str  # SHA256 hash of the actual key
    name: str
    role: Role
    created_at: float
    created_by: str
    last_used: Optional[float] = None
    revoked: bool = False
    revoked_at: Optional[float] = None
    revoked_by: Optional[str] = None


@dataclass
class RefreshToken:
    """Refresh token for JWT renewal."""

    token_id: str
    token_hash: str
    user_id: str
    expires_at: float
    created_at: float
    revoked: bool = False


# ---------------------------------------------------------------------------
# Pydantic Models (API)
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Login request with username and password."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class LoginResponse(BaseModel):
    """Login response with tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class APIKeyCreateRequest(BaseModel):
    """Request to create an API key."""

    name: str = Field(..., min_length=3, max_length=64, description="Human-readable key name")
    role: Role = Field(..., description="Role for this API key")


class APIKeyCreateResponse(BaseModel):
    """Response with new API key (only shown once!)."""

    key_id: str
    api_key: str  # Full key, only shown once
    name: str
    role: str
    created_at: float
    warning: str = "SAVE THIS KEY - it will not be shown again!"


class APIKeyInfo(BaseModel):
    """API key information (without the actual key)."""

    key_id: str
    name: str
    role: str
    created_at: float
    created_by: str
    last_used: Optional[float] = None
    revoked: bool = False


class APIKeyListResponse(BaseModel):
    """List of API keys."""

    keys: List[APIKeyInfo]


class AuthPrincipal(BaseModel):
    """Authenticated principal (user or service account)."""

    user_id: str
    username: str
    role: Role
    auth_method: str  # "jwt" or "apikey"
    key_id: Optional[str] = None  # Set if authenticated via API key


# ---------------------------------------------------------------------------
# In-Memory Stores (migrate to DB in production)
# ---------------------------------------------------------------------------


class AuthStore:
    """In-memory authentication store."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self.refresh_tokens: Dict[str, RefreshToken] = {}  # token_id -> RefreshToken

        # Create default admin user
        self._create_default_admin()

    def _create_default_admin(self):
        """Create default admin user if not exists."""
        admin_hash = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
        self.users[DEFAULT_ADMIN_USERNAME] = User(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=admin_hash,
            role=Role.ADMIN,
        )
        logger.info(f"Default admin user created: {DEFAULT_ADMIN_USERNAME}")

    def create_user(self, username: str, password: str, role: Role) -> User:
        """Create a new user."""
        if username in self.users:
            raise ValueError(f"User {username} already exists")

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user = User(username=username, password_hash=password_hash, role=role)
        self.users[username] = user
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username/password."""
        user = self.users.get(username)
        if not user:
            return None

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash != user.password_hash:
            return None

        user.last_login = time.time()
        return user

    def create_api_key(self, name: str, role: Role, created_by: str) -> tuple[APIKey, str]:
        """Create a new API key. Returns (APIKey, actual_key)."""
        key_id = f"nk_{uuid.uuid4().hex[:16]}"  # neutron key
        actual_key = f"{key_id}_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(actual_key.encode()).hexdigest()

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            role=role,
            created_at=time.time(),
            created_by=created_by,
        )
        self.api_keys[key_id] = api_key
        return api_key, actual_key

    def verify_api_key(self, api_key: str) -> Optional[APIKey]:
        """Verify API key and return APIKey object if valid."""
        # Extract key_id from the key (format: nk_xxxxx_yyyyyy)
        parts = api_key.split("_", 2)
        if len(parts) != 3 or parts[0] != "nk":
            return None

        key_id = f"{parts[0]}_{parts[1]}"
        stored_key = self.api_keys.get(key_id)
        if not stored_key:
            return None

        if stored_key.revoked:
            return None

        # Verify hash
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if key_hash != stored_key.key_hash:
            return None

        # Update last_used
        stored_key.last_used = time.time()
        return stored_key

    def revoke_api_key(self, key_id: str, revoked_by: str) -> bool:
        """Revoke an API key."""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False

        api_key.revoked = True
        api_key.revoked_at = time.time()
        api_key.revoked_by = revoked_by
        return True

    def list_api_keys(self, include_revoked: bool = False) -> List[APIKey]:
        """List all API keys."""
        keys = list(self.api_keys.values())
        if not include_revoked:
            keys = [k for k in keys if not k.revoked]
        return keys

    def create_refresh_token(self, user_id: str) -> str:
        """Create a refresh token."""
        token_id = uuid.uuid4().hex
        actual_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(actual_token.encode()).hexdigest()

        refresh_token = RefreshToken(
            token_id=token_id,
            token_hash=token_hash,
            user_id=user_id,
            expires_at=time.time() + REFRESH_TOKEN_EXPIRATION_SECONDS,
            created_at=time.time(),
        )
        self.refresh_tokens[token_id] = refresh_token
        return actual_token

    def verify_refresh_token(self, token: str) -> Optional[str]:
        """Verify refresh token and return user_id if valid."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Find token by hash (not efficient, but OK for in-memory)
        for refresh_token in self.refresh_tokens.values():
            if refresh_token.token_hash == token_hash:
                if refresh_token.revoked:
                    return None
                if refresh_token.expires_at < time.time():
                    return None
                return refresh_token.user_id

        return None

    def revoke_refresh_token(self, token: str):
        """Revoke a refresh token."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        for refresh_token in self.refresh_tokens.values():
            if refresh_token.token_hash == token_hash:
                refresh_token.revoked = True
                break


# Global store instance
_auth_store = AuthStore()


def get_auth_store() -> AuthStore:
    """Get the global auth store."""
    return _auth_store


# ---------------------------------------------------------------------------
# JWT Helpers (imported from server.py, enhanced)
# ---------------------------------------------------------------------------

import base64
import hmac
import json


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def jwt_sign(payload: dict, secret: str) -> str:
    """Sign a JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    segments: list[str] = [
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode()),
        _b64url_encode(json.dumps(payload, separators=(",", ":")).encode()),
    ]
    signing_input = f"{segments[0]}.{segments[1]}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url_encode(signature))
    return ".".join(segments)


def jwt_verify(token: str, secret: str) -> dict:
    """Verify and decode a JWT token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token structure")
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(parts[2])
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid signature")
    payload = json.loads(_b64url_decode(parts[1]))
    if "exp" in payload and payload["exp"] < time.time():
        raise ValueError("Token expired")
    return payload


# ---------------------------------------------------------------------------
# Authentication Dependencies
# ---------------------------------------------------------------------------


async def get_current_user(request: Request) -> AuthPrincipal:
    """
    Dependency that extracts and validates authentication.

    Supports two methods:
    1. Bearer JWT token (Authorization: Bearer <token>)
    2. API Key (X-API-Key: <key>)

    If API_SECRET_KEY is not configured, runs in open mode (anonymous user).
    """
    if not API_SECRET_KEY:
        # Open mode - no authentication required
        logger.warning("API running in OPEN MODE - no authentication required!")
        return AuthPrincipal(
            user_id="anonymous",
            username="anonymous",
            role=Role.ADMIN,  # Full access in open mode
            auth_method="none",
        )

    auth_store = get_auth_store()

    # Check for API Key first
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        api_key_obj = auth_store.verify_api_key(api_key_header)
        if not api_key_obj:
            logger.warning("Invalid API key attempted")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
            )

        logger.info(f"Authenticated via API key: {api_key_obj.key_id} ({api_key_obj.name})")
        return AuthPrincipal(
            user_id=api_key_obj.key_id,
            username=api_key_obj.name,
            role=api_key_obj.role,
            auth_method="apikey",
            key_id=api_key_obj.key_id,
        )

    # Check for Bearer token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Provide either 'Authorization: Bearer <token>' or 'X-API-Key: <key>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]
    try:
        payload = jwt_verify(token, API_SECRET_KEY)
    except ValueError as exc:
        logger.warning(f"JWT verification failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user info from JWT
    user_id = payload.get("sub")
    role_str = payload.get("role", "auditor")

    logger.info(f"Authenticated via JWT: {user_id} (role: {role_str})")
    return AuthPrincipal(
        user_id=user_id,
        username=user_id,
        role=Role(role_str),
        auth_method="jwt",
    )


def require_role(required_role: Role):
    """
    Dependency factory for role-based access control.

    Usage:
        @app.get("/admin", dependencies=[Depends(require_role(Role.ADMIN))])
        async def admin_endpoint():
            ...
    """

    async def role_checker(principal: AuthPrincipal = Depends(get_current_user)) -> AuthPrincipal:
        # Check if user's role is in the hierarchy of required role
        allowed_roles = ROLE_HIERARCHY.get(principal.role, [])
        if required_role not in allowed_roles:
            logger.warning(
                f"Access denied: user {principal.username} (role: {principal.role}) "
                f"attempted to access endpoint requiring {required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}, your role: {principal.role}",
            )
        return principal

    return role_checker


# ---------------------------------------------------------------------------
# Auth Helper Functions
# ---------------------------------------------------------------------------


def create_access_token(user_id: str, role: Role) -> tuple[str, int]:
    """Create an access token (JWT). Returns (token, expires_in)."""
    if not API_SECRET_KEY:
        raise RuntimeError("API_SECRET_KEY not configured")

    now = time.time()
    payload = {
        "sub": user_id,
        "role": role.value,
        "iat": int(now),
        "exp": int(now + JWT_EXPIRATION_SECONDS),
        "jti": str(uuid.uuid4()),
    }
    token = jwt_sign(payload, API_SECRET_KEY)
    return token, JWT_EXPIRATION_SECONDS


def audit_log_auth_event(event_type: str, user_id: str, details: Dict[str, Any]):
    """Log authentication events for audit trail."""
    logger.info(
        f"AUTH_AUDIT: event={event_type} user={user_id} details={json.dumps(details)}"
    )
    # TODO: Send to compliance audit logger (neutron.compliance.audit_logger)
