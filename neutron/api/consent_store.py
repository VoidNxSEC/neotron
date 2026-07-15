"""
Consent Management Store

LGPD Article 7: Consent as legal basis for data processing.
LGPD Article 8: Consent must be provided in writing or other means.
LGPD Article 18: Right to revoke consent at any time.
GDPR Article 7: Conditions for consent.
"""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConsentStatus(str, Enum):
    """Consent token status."""

    ACTIVE = "active"  # Currently valid
    REVOKED = "revoked"  # User revoked (LGPD Art 18)
    EXPIRED = "expired"  # Time-based expiry
    SUPERSEDED = "superseded"  # Replaced by newer version


class ConsentPurpose(str, Enum):
    """Purpose of data processing."""

    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    SERVICE_IMPROVEMENT = "service_improvement"
    LEGAL_OBLIGATION = "legal_obligation"
    CONTRACT_PERFORMANCE = "contract_performance"
    RESEARCH = "research"
    THIRD_PARTY_SHARING = "third_party_sharing"


class DataType(str, Enum):
    """Types of personal data."""

    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    CPF = "cpf"  # Brazilian tax ID
    FINANCIAL_DATA = "financial_data"
    HEALTH_DATA = "health_data"
    BIOMETRIC_DATA = "biometric_data"
    LOCATION_DATA = "location_data"
    BROWSING_HISTORY = "browsing_history"
    IP_ADDRESS = "ip_address"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class ConsentToken:
    """Consent token with granular permissions."""

    token_id: str
    customer_id: str
    token_hash: str  # SHA256 hash of actual token
    status: ConsentStatus
    version: int  # Consent versioning
    regulation: str  # LGPD, GDPR, etc.
    purposes: list[ConsentPurpose] = field(default_factory=list)
    data_types: list[DataType] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None  # None = no expiry
    revoked_at: float | None = None
    revoked_reason: str | None = None
    superseded_by: str | None = None  # Token ID that replaced this
    metadata: dict[str, Any] = field(default_factory=dict)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pydantic Models (API)
# ---------------------------------------------------------------------------


class ConsentCreateRequest(BaseModel):
    """Request to create consent token."""

    customer_id: str = Field(..., min_length=3, max_length=128)
    regulation: str = Field(default="LGPD", description="LGPD, GDPR, etc.")
    purposes: list[ConsentPurpose] = Field(..., min_items=1, description="Processing purposes")
    data_types: list[DataType] = Field(..., min_items=1, description="Data types covered")
    expires_in_days: int | None = Field(
        None, ge=1, le=3650, description="Expiry in days (max 10 years)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConsentRevokeRequest(BaseModel):
    """Request to revoke consent."""

    reason: str | None = Field(None, max_length=512, description="Reason for revocation")


class ConsentTokenResponse(BaseModel):
    """Consent token response."""

    token_id: str
    customer_id: str
    consent_token: str | None = None  # Full token (only shown on creation!)
    status: str
    version: int
    regulation: str
    purposes: list[str]
    data_types: list[str]
    created_at: float
    expires_at: float | None = None
    revoked_at: float | None = None
    revoked_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    warning: str | None = None


class ConsentVerifyResponse(BaseModel):
    """Consent verification response."""

    valid: bool
    token_id: str
    customer_id: str
    status: str
    purposes: list[str]
    data_types: list[str]
    expires_at: float | None = None
    reason: str | None = None  # Why invalid


class ConsentListResponse(BaseModel):
    """List of consents."""

    consents: list[ConsentTokenResponse]
    total: int


# ---------------------------------------------------------------------------
# Consent Store
# ---------------------------------------------------------------------------


class ConsentStore:
    """In-memory consent store (migrate to DB in production)."""

    def __init__(self):
        self.consents: dict[str, ConsentToken] = {}  # token_id -> ConsentToken
        self._index_by_customer: dict[str, list[str]] = {}  # customer_id -> [token_ids]
        self._token_hash_to_id: dict[str, str] = {}  # token_hash -> token_id

    def create_consent(
        self,
        customer_id: str,
        regulation: str,
        purposes: list[ConsentPurpose],
        data_types: list[DataType],
        expires_in_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[ConsentToken, str]:
        """
        Create a new consent token.

        Returns: (ConsentToken, actual_token)
        """
        token_id = f"consent_{uuid.uuid4().hex[:16]}"

        # Generate secure token
        actual_token = f"{token_id}_{secrets.token_urlsafe(32)}"
        token_hash = hashlib.sha256(actual_token.encode()).hexdigest()

        # Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = time.time() + (expires_in_days * 24 * 60 * 60)

        # Check for existing active consents (for versioning)
        customer_tokens = self._index_by_customer.get(customer_id, [])
        active_tokens = [
            self.consents[tid]
            for tid in customer_tokens
            if self.consents[tid].status == ConsentStatus.ACTIVE
            and self.consents[tid].regulation == regulation
        ]

        version = 1
        if active_tokens:
            # Supersede old consents
            for old_token in active_tokens:
                old_token.status = ConsentStatus.SUPERSEDED
                old_token.superseded_by = token_id
                old_token.audit_trail.append(
                    {
                        "action": "superseded",
                        "timestamp": time.time(),
                        "superseded_by": token_id,
                    }
                )

            # Increment version
            version = max(t.version for t in active_tokens) + 1

        consent = ConsentToken(
            token_id=token_id,
            customer_id=customer_id,
            token_hash=token_hash,
            status=ConsentStatus.ACTIVE,
            version=version,
            regulation=regulation,
            purposes=purposes,
            data_types=data_types,
            expires_at=expires_at,
            metadata=metadata or {},
            audit_trail=[
                {
                    "action": "created",
                    "timestamp": time.time(),
                    "purposes": [p.value for p in purposes],
                    "data_types": [d.value for d in data_types],
                }
            ],
        )

        self.consents[token_id] = consent
        self._token_hash_to_id[token_hash] = token_id

        # Update customer index
        if customer_id not in self._index_by_customer:
            self._index_by_customer[customer_id] = []
        self._index_by_customer[customer_id].append(token_id)

        return consent, actual_token

    def verify_consent(self, consent_token: str) -> tuple[bool, ConsentToken | None, str | None]:
        """
        Verify a consent token.

        Returns: (valid, ConsentToken or None, reason if invalid)
        """
        # Extract token_id and hash
        parts = consent_token.split("_", 2)
        if len(parts) != 3 or parts[0] != "consent":
            return False, None, "Invalid token format"

        token_hash = hashlib.sha256(consent_token.encode()).hexdigest()
        token_id = self._token_hash_to_id.get(token_hash)

        if not token_id:
            return False, None, "Token not found"

        consent = self.consents.get(token_id)
        if not consent:
            return False, None, "Token not found"

        # Check status
        if consent.status == ConsentStatus.REVOKED:
            return False, consent, "Consent revoked by user"

        if consent.status == ConsentStatus.SUPERSEDED:
            return False, consent, "Consent superseded by newer version"

        # Check expiry
        if consent.expires_at and consent.expires_at < time.time():
            # Mark as expired
            consent.status = ConsentStatus.EXPIRED
            consent.audit_trail.append(
                {
                    "action": "expired",
                    "timestamp": time.time(),
                }
            )
            return False, consent, "Consent expired"

        if consent.status != ConsentStatus.ACTIVE:
            return False, consent, f"Consent status: {consent.status.value}"

        # Verify hash
        if token_hash != consent.token_hash:
            return False, None, "Invalid token hash"

        return True, consent, None

    def revoke_consent(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> ConsentToken | None:
        """
        Revoke a consent token (LGPD Article 18).

        Returns: ConsentToken if found, None otherwise
        """
        consent = self.consents.get(token_id)
        if not consent:
            return None

        if consent.status == ConsentStatus.REVOKED:
            # Already revoked
            return consent

        # Revoke
        consent.status = ConsentStatus.REVOKED
        consent.revoked_at = time.time()
        consent.revoked_reason = reason

        consent.audit_trail.append(
            {
                "action": "revoked",
                "timestamp": time.time(),
                "reason": reason,
            }
        )

        return consent

    def get_consent_by_id(self, token_id: str) -> ConsentToken | None:
        """Get consent by token ID."""
        return self.consents.get(token_id)

    def list_customer_consents(
        self,
        customer_id: str,
        include_revoked: bool = False,
    ) -> list[ConsentToken]:
        """List all consents for a customer."""
        token_ids = self._index_by_customer.get(customer_id, [])
        consents = [self.consents[tid] for tid in token_ids]

        if not include_revoked:
            consents = [
                c
                for c in consents
                if c.status not in [ConsentStatus.REVOKED, ConsentStatus.SUPERSEDED]
            ]

        # Sort by created_at (newest first)
        consents.sort(key=lambda x: x.created_at, reverse=True)

        return consents

    def check_purpose_consent(
        self,
        customer_id: str,
        purpose: ConsentPurpose,
        regulation: str = "LGPD",
    ) -> bool:
        """
        Check if customer has active consent for a specific purpose.

        Use case: Before processing data, check "can I use this data for marketing?"
        """
        consents = self.list_customer_consents(customer_id, include_revoked=False)

        for consent in consents:
            if (
                consent.status == ConsentStatus.ACTIVE
                and consent.regulation == regulation
                and purpose in consent.purposes
            ):
                # Check expiry
                if consent.expires_at and consent.expires_at < time.time():
                    continue
                return True

        return False

    def check_data_type_consent(
        self,
        customer_id: str,
        data_type: DataType,
        regulation: str = "LGPD",
    ) -> bool:
        """
        Check if customer has active consent for processing a specific data type.

        Use case: Before accessing email, check "can I process this customer's email?"
        """
        consents = self.list_customer_consents(customer_id, include_revoked=False)

        for consent in consents:
            if (
                consent.status == ConsentStatus.ACTIVE
                and consent.regulation == regulation
                and data_type in consent.data_types
            ):
                # Check expiry
                if consent.expires_at and consent.expires_at < time.time():
                    continue
                return True

        return False


# Global store instance
_consent_store = ConsentStore()


def get_consent_store() -> ConsentStore:
    """Get the global consent store."""
    return _consent_store
