"""
Compliance API Endpoints

Exposes the 4-layer NEXUS compliance flow via REST API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from neutron.compliance.nexus_flow import (
    ComplianceDecision,
    ComplianceRequest,
    ComplianceResponse,
    NEXUSComplianceFlow,
)

logger = logging.getLogger("neutron.api.compliance")

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])

# Global flow instance (singleton)
_flow_instance: Optional[NEXUSComplianceFlow] = None


def get_flow() -> NEXUSComplianceFlow:
    """Get or create the global compliance flow instance."""
    global _flow_instance
    if _flow_instance is None:
        import os

        _flow_instance = NEXUSComplianceFlow(
            enable_bastion=os.getenv("ENABLE_BASTION", "true").lower() == "true",
            enable_smart_contracts=os.getenv("ENABLE_SMART_CONTRACTS", "false").lower()
            == "true",
            enable_memory=os.getenv("ENABLE_MEMORY", "true").lower() == "true",
        )
    return _flow_instance


# Request/Response models


class ComplianceValidateRequest(BaseModel):
    """Request to validate compliance for an action."""

    customer_id: str = Field(..., description="Customer/user identifier")
    action: str = Field(
        ..., description="Action to validate (e.g., loan_approval, data_processing)"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Action-specific data"
    )
    consent_token: Optional[str] = Field(
        None, description="LGPD/GDPR consent token"
    )
    regulation: str = Field(
        default="LGPD", description="Regulation to enforce (LGPD, GDPR, AI_ACT)"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class LayerResultResponse(BaseModel):
    """Result from a single compliance layer."""

    layer_name: str
    passed: bool
    status: str
    details: str
    processing_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ComplianceValidateResponse(BaseModel):
    """Response from compliance validation."""

    request_id: str
    decision: str  # APPROVED, REJECTED, CONDITIONAL, REVIEW_REQUIRED
    confidence: float
    explanation: str
    audit_hash: str
    layers: Dict[str, LayerResultResponse]
    total_processing_time_ms: float
    blockchain_tx: Optional[str] = None
    timestamp: float


class CompliancePolicyListResponse(BaseModel):
    """List of available compliance policies."""

    policies: list[dict]


class ComplianceHealthResponse(BaseModel):
    """Health check for compliance system."""

    status: str
    layers: Dict[str, dict]
    version: str


# Endpoints


@router.post("/validate", response_model=ComplianceValidateResponse)
async def validate_compliance(
    request: ComplianceValidateRequest,
) -> ComplianceValidateResponse:
    """
    Validate an action through the 4-layer NEXUS compliance flow.

    **Flow**:
    1. **SENTINEL** (Layer 1): Application-level validation
    2. **BASTION** (Layer 2): Kernel-level enforcement
    3. **CORTEX** (Layer 3): Multi-agent LLM decision + ORACLE explanation
    4. **AUDIT** (Layer 4): Immutable log to IPFS/Arweave

    **Returns**:
    - `decision`: APPROVED, REJECTED, CONDITIONAL, or REVIEW_REQUIRED
    - `audit_hash`: IPFS CID for permanent audit trail
    - `layers`: Detailed results from each layer

    **Example**:
    ```json
    {
      "customer_id": "customer_123",
      "action": "loan_approval",
      "data": {"credit_score": 720, "amount": 10000},
      "consent_token": "lgpd_consent_abc123",
      "regulation": "LGPD"
    }
    ```
    """
    logger.info(
        f"Compliance validation request: action={request.action}, "
        f"customer={request.customer_id}, regulation={request.regulation}"
    )

    try:
        flow = get_flow()

        # Build compliance request
        compliance_req = ComplianceRequest(
            customer_id=request.customer_id,
            action=request.action,
            data=request.data,
            consent_token=request.consent_token,
            regulation=request.regulation,
            metadata=request.metadata,
        )

        # Execute 4-layer flow
        response = await flow.validate(compliance_req)

        # Convert to API response
        return ComplianceValidateResponse(
            request_id=response.request_id,
            decision=response.decision.value,
            confidence=response.confidence,
            explanation=response.explanation,
            audit_hash=response.audit_hash,
            layers={
                name: LayerResultResponse(
                    layer_name=layer.layer_name,
                    passed=layer.passed,
                    status=layer.status,
                    details=layer.details,
                    processing_time_ms=layer.processing_time_ms,
                    metadata=layer.metadata,
                    error=layer.error,
                )
                for name, layer in response.layers.items()
            },
            total_processing_time_ms=response.total_processing_time_ms,
            blockchain_tx=response.blockchain_tx,
            timestamp=response.timestamp,
        )

    except Exception as e:
        logger.error(f"Compliance validation error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Compliance validation failed: {str(e)}")


@router.get("/policies", response_model=CompliancePolicyListResponse)
async def list_policies() -> CompliancePolicyListResponse:
    """
    List available compliance policies and regulations.

    Returns details about supported regulations (LGPD, GDPR, AI Act)
    and their implemented guardrails.
    """
    policies = [
        {
            "regulation": "LGPD",
            "name": "Lei Geral de Proteção de Dados (Brazil)",
            "articles": [7, 18, 20],
            "guardrails": ["consent_validation", "right_to_explanation", "data_portability"],
            "enforcement_layers": 4,
        },
        {
            "regulation": "GDPR",
            "name": "General Data Protection Regulation (EU)",
            "articles": [6, 13, 14, 22],
            "guardrails": ["lawful_basis", "transparency", "automated_decisions"],
            "enforcement_layers": 4,
        },
        {
            "regulation": "AI_ACT",
            "name": "EU AI Act",
            "articles": [13, 14],
            "guardrails": ["transparency", "human_oversight", "risk_management"],
            "enforcement_layers": 4,
        },
    ]

    return CompliancePolicyListResponse(policies=policies)


@router.get("/health", response_model=ComplianceHealthResponse)
async def health_check() -> ComplianceHealthResponse:
    """
    Health check for compliance system.

    Returns status of all 4 layers and their availability.
    """
    flow = get_flow()

    # Check each layer's health
    layers_health = {
        "SENTINEL": {
            "available": True,
            "status": "operational",
            "description": "Application-level validation",
        },
        "BASTION": {
            "available": flow.enable_bastion,
            "status": "operational" if flow.enable_bastion else "disabled",
            "description": "Kernel-level enforcement (seccomp-BPF)",
        },
        "CORTEX": {
            "available": True,
            "status": "operational",
            "description": "Multi-agent LLM + ORACLE explainability",
        },
        "AUDIT": {
            "available": True,
            "status": "operational",
            "description": "Immutable audit trail (IPFS/Arweave)",
        },
    }

    return ComplianceHealthResponse(
        status="healthy",
        layers=layers_health,
        version="0.1.0",
    )


@router.get("/audit/{audit_hash}")
async def get_audit_log(audit_hash: str) -> Dict[str, Any]:
    """
    Retrieve audit log by hash (IPFS CID or Arweave TX).

    Fetches the immutable compliance log from decentralized storage
    (IPFS, Arweave, or local fallback).
    """
    from neutron.storage.decentralized import DecentralizedStorage, StorageType

    storage = DecentralizedStorage()

    # Try local first (most common in dev), then IPFS, then Arweave
    for storage_type in [StorageType.LOCAL, StorageType.IPFS, StorageType.ARWEAVE]:
        try:
            log = await storage.retrieve_log(storage_type, audit_hash)
            return {
                "audit_hash": audit_hash,
                "status": "found",
                "storage_type": storage_type.value,
                "log": {
                    "log_id": log.log_id,
                    "user_address": log.user_address,
                    "regulation": log.regulation,
                    "article": log.article,
                    "action": log.action,
                    "passed": log.passed,
                    "violation": log.violation,
                    "timestamp": log.timestamp,
                    "metadata": log.metadata,
                    "blockchain_tx": log.blockchain_tx,
                },
            }
        except (ValueError, Exception):
            continue

    raise HTTPException(
        status_code=404,
        detail=f"Audit log not found for hash: {audit_hash}",
    )
