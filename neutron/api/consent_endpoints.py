"""
Consent Management API Endpoints

LGPD Article 7, 8, 18 - Consent management
GDPR Article 7 - Conditions for consent
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from neutron.api.auth import AuthPrincipal, Role, get_current_user, require_role
from neutron.api.consent_store import (
    ConsentCreateRequest,
    ConsentListResponse,
    ConsentRevokeRequest,
    ConsentTokenResponse,
    ConsentVerifyResponse,
    get_consent_store,
)

logger = logging.getLogger("neutron.api.consent_endpoints")

router = APIRouter(prefix="/v1/consent", tags=["consent"])


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def consent_to_response(
    consent, include_token: bool = False, actual_token: str | None = None
) -> ConsentTokenResponse:
    """Convert ConsentToken to ConsentTokenResponse."""
    return ConsentTokenResponse(
        token_id=consent.token_id,
        customer_id=consent.customer_id,
        consent_token=actual_token if include_token else None,
        status=consent.status.value,
        version=consent.version,
        regulation=consent.regulation,
        purposes=[p.value for p in consent.purposes],
        data_types=[d.value for d in consent.data_types],
        created_at=consent.created_at,
        expires_at=consent.expires_at,
        revoked_at=consent.revoked_at,
        revoked_reason=consent.revoked_reason,
        metadata=consent.metadata,
        warning="SAVE THIS TOKEN - it will not be shown again!" if include_token else None,
    )


# ---------------------------------------------------------------------------
# Endpoints - Consent Token Management
# ---------------------------------------------------------------------------


@router.post(
    "/tokens",
    response_model=ConsentTokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.OPERATOR))],
)
async def create_consent_token(
    request: ConsentCreateRequest,
    principal: AuthPrincipal = Depends(get_current_user),
) -> ConsentTokenResponse:
    """
    Create a new consent token (OPERATOR or ADMIN).

    **LGPD Article 7**: Consent as legal basis for data processing.
    **LGPD Article 8**: Consent must be in writing or other demonstrable means.

    **Example**:
    ```json
    {
      "customer_id": "customer_br_123",
      "regulation": "LGPD",
      "purposes": ["marketing", "analytics"],
      "data_types": ["email", "phone"],
      "expires_in_days": 365,
      "metadata": {"consent_method": "web_form", "ip": "192.168.1.1"}
    }
    ```

    **WARNING**: The full consent token is only shown ONCE on creation!
    """
    consent_store = get_consent_store()

    # Create consent
    consent, actual_token = consent_store.create_consent(
        customer_id=request.customer_id,
        regulation=request.regulation,
        purposes=request.purposes,
        data_types=request.data_types,
        expires_in_days=request.expires_in_days,
        metadata=request.metadata,
    )

    logger.info(
        f"Consent created: {consent.token_id} for customer {request.customer_id}, "
        f"purposes={[p.value for p in request.purposes]}, by {principal.username}"
    )

    # Log audit event
    from neutron.api.audit_store import AuditEventType, get_audit_store

    audit_store = get_audit_store()
    audit_store.log_event(
        event_type=AuditEventType.CONSENT_GRANTED,
        customer_id=request.customer_id,
        user_id=principal.username,
        action="consent_created",
        regulation=request.regulation,
        details={
            "token_id": consent.token_id,
            "purposes": [p.value for p in request.purposes],
            "data_types": [d.value for d in request.data_types],
            "version": consent.version,
        },
    )

    return consent_to_response(consent, include_token=True, actual_token=actual_token)


@router.get("/tokens/{token_id}", response_model=ConsentTokenResponse)
async def get_consent_token(
    token_id: str,
    principal: AuthPrincipal = Depends(get_current_user),
) -> ConsentTokenResponse:
    """
    Get consent token details by ID.

    **Note**: The full token is NOT returned (security). Only metadata.

    **Example**: `GET /v1/consent/tokens/consent_abc123`
    """
    consent_store = get_consent_store()

    consent = consent_store.get_consent_by_id(token_id)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent token not found: {token_id}",
        )

    return consent_to_response(consent, include_token=False)


@router.post("/verify", response_model=ConsentVerifyResponse)
async def verify_consent_token(
    consent_token: str = Query(..., description="Full consent token to verify"),
    principal: AuthPrincipal = Depends(get_current_user),
) -> ConsentVerifyResponse:
    """
    Verify if a consent token is valid.

    **Use case**: Before processing data, verify customer consent is still active.

    **Example**: `POST /v1/consent/verify?consent_token=consent_abc123_xyz...`

    **Returns**:
    - `valid`: true if active and not expired
    - `reason`: Why invalid (if applicable)
    """
    consent_store = get_consent_store()

    valid, consent, reason = consent_store.verify_consent(consent_token)

    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent token not found or invalid: {reason}",
        )

    logger.info(
        f"Consent verified: {consent.token_id}, valid={valid}, "
        f"customer={consent.customer_id}, requester={principal.username}"
    )

    return ConsentVerifyResponse(
        valid=valid,
        token_id=consent.token_id,
        customer_id=consent.customer_id,
        status=consent.status.value,
        purposes=[p.value for p in consent.purposes],
        data_types=[d.value for d in consent.data_types],
        expires_at=consent.expires_at,
        reason=reason,
    )


@router.delete(
    "/tokens/{token_id}",
    response_model=ConsentTokenResponse,
)
async def revoke_consent_token(
    token_id: str,
    request: ConsentRevokeRequest | None = None,
    principal: AuthPrincipal = Depends(get_current_user),
) -> ConsentTokenResponse:
    """
    Revoke a consent token (LGPD Article 18 - Right to Revoke).

    **LGPD Article 18**: Data subject has the right to revoke consent at any time.

    **Example**:
    ```
    DELETE /v1/consent/tokens/consent_abc123
    {
      "reason": "User requested data processing stop"
    }
    ```

    **Note**: Revocation is permanent and audited.
    """
    consent_store = get_consent_store()

    reason = request.reason if request else None

    consent = consent_store.revoke_consent(token_id, reason=reason)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent token not found: {token_id}",
        )

    logger.info(
        f"Consent revoked: {token_id}, customer={consent.customer_id}, "
        f"reason={reason}, requester={principal.username}"
    )

    # Log audit event
    from neutron.api.audit_store import AuditEventType, get_audit_store

    audit_store = get_audit_store()
    audit_store.log_event(
        event_type=AuditEventType.CONSENT_REVOKED,
        customer_id=consent.customer_id,
        user_id=principal.username,
        action="consent_revoked",
        regulation=consent.regulation,
        details={
            "token_id": token_id,
            "reason": reason,
            "version": consent.version,
        },
    )

    return consent_to_response(consent, include_token=False)


# ---------------------------------------------------------------------------
# Endpoints - Customer Consent Management
# ---------------------------------------------------------------------------


@router.get("/customer/{customer_id}", response_model=ConsentListResponse)
async def list_customer_consents(
    customer_id: str,
    include_revoked: bool = Query(False, description="Include revoked consents"),
    principal: AuthPrincipal = Depends(get_current_user),
) -> ConsentListResponse:
    """
    List all consents for a specific customer.

    **LGPD Article 18**: Right to access consent history.
    **GDPR Article 15**: Right of access.

    **Use case**: Customer requests "show me all my consents"

    **Example**: `GET /v1/consent/customer/customer_br_123?include_revoked=false`
    """
    consent_store = get_consent_store()

    consents = consent_store.list_customer_consents(
        customer_id=customer_id,
        include_revoked=include_revoked,
    )

    logger.info(
        f"Customer consents listed: customer={customer_id}, count={len(consents)}, "
        f"requester={principal.username}"
    )

    return ConsentListResponse(
        consents=[consent_to_response(c, include_token=False) for c in consents],
        total=len(consents),
    )


@router.get("/customer/{customer_id}/check")
async def check_customer_consent(
    customer_id: str,
    purpose: str | None = Query(None, description="Check specific purpose (e.g., marketing)"),
    data_type: str | None = Query(None, description="Check specific data type (e.g., email)"),
    regulation: str = Query("LGPD", description="Regulation (LGPD, GDPR, etc.)"),
    principal: AuthPrincipal = Depends(get_current_user),
) -> dict:
    """
    Check if customer has active consent for a purpose or data type.

    **Use case**: Before processing, check "can I use this customer's email for marketing?"

    **Example**: `GET /v1/consent/customer/cust_123/check?purpose=marketing&data_type=email`

    **Returns**:
    ```json
    {
      "customer_id": "cust_123",
      "has_consent": true,
      "purpose": "marketing",
      "data_type": "email",
      "regulation": "LGPD"
    }
    ```
    """
    consent_store = get_consent_store()

    has_consent = False

    if purpose:
        from neutron.api.consent_store import ConsentPurpose

        try:
            purpose_enum = ConsentPurpose(purpose)
            has_consent = consent_store.check_purpose_consent(
                customer_id=customer_id,
                purpose=purpose_enum,
                regulation=regulation,
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid purpose: {purpose}",
            )

    elif data_type:
        from neutron.api.consent_store import DataType

        try:
            data_type_enum = DataType(data_type)
            has_consent = consent_store.check_data_type_consent(
                customer_id=customer_id,
                data_type=data_type_enum,
                regulation=regulation,
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data_type: {data_type}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'purpose' or 'data_type' parameter",
        )

    logger.info(
        f"Consent check: customer={customer_id}, purpose={purpose}, "
        f"data_type={data_type}, has_consent={has_consent}"
    )

    return {
        "customer_id": customer_id,
        "has_consent": has_consent,
        "purpose": purpose,
        "data_type": data_type,
        "regulation": regulation,
    }
