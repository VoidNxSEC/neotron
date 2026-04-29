"""
Policy Store - Custom Compliance Policy Management

Allows enterprises to define, store, and manage custom compliance policies.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PolicyType(str, Enum):
    """Types of compliance policies."""

    LGPD = "LGPD"
    GDPR = "GDPR"
    AI_ACT = "AI_ACT"
    HIPAA = "HIPAA"
    CUSTOM = "CUSTOM"


class PolicySeverity(str, Enum):
    """Severity levels for policy violations."""

    BLOCK = "block"  # Block request immediately
    WARN = "warn"  # Log warning but allow
    AUDIT = "audit"  # Record for audit only


class PolicyStatus(str, Enum):
    """Policy lifecycle status."""

    DRAFT = "draft"  # Being edited, not enforced
    ACTIVE = "active"  # Currently enforced
    INACTIVE = "inactive"  # Temporarily disabled
    ARCHIVED = "archived"  # Historical, not enforced


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class PolicyRule:
    """Individual compliance rule within a policy."""

    rule_id: str
    name: str
    description: str
    condition: dict[
        str, Any
    ]  # JSON condition (e.g., {"field": "age", "operator": ">=", "value": 18})
    action: PolicySeverity
    error_message: str | None = None


@dataclass
class CompliancePolicy:
    """Custom compliance policy."""

    policy_id: str
    name: str
    description: str
    policy_type: PolicyType
    version: str
    status: PolicyStatus
    rules: list[PolicyRule] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    created_by: str = ""
    updated_at: float | None = None
    updated_by: str | None = None
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pydantic Models (API)
# ---------------------------------------------------------------------------


class PolicyRuleCreate(BaseModel):
    """Request to create a policy rule."""

    name: str = Field(..., min_length=3, max_length=128)
    description: str = Field(..., min_length=10, max_length=512)
    condition: dict[str, Any] = Field(..., description="JSON condition for rule evaluation")
    action: PolicySeverity = Field(default=PolicySeverity.BLOCK)
    error_message: str | None = Field(None, max_length=256)


class PolicyRuleResponse(BaseModel):
    """Policy rule response."""

    rule_id: str
    name: str
    description: str
    condition: dict[str, Any]
    action: str
    error_message: str | None = None


class PolicyCreateRequest(BaseModel):
    """Request to create a compliance policy."""

    name: str = Field(..., min_length=3, max_length=128)
    description: str = Field(..., min_length=10, max_length=1024)
    policy_type: PolicyType
    rules: list[PolicyRuleCreate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class PolicyUpdateRequest(BaseModel):
    """Request to update a policy."""

    name: str | None = Field(None, min_length=3, max_length=128)
    description: str | None = Field(None, min_length=10, max_length=1024)
    status: PolicyStatus | None = None
    rules: list[PolicyRuleCreate] | None = None
    metadata: dict[str, Any] | None = None
    tags: list[str] | None = None


class PolicyResponse(BaseModel):
    """Policy response."""

    policy_id: str
    name: str
    description: str
    policy_type: str
    version: str
    status: str
    rules: list[PolicyRuleResponse]
    metadata: dict[str, Any]
    created_at: float
    created_by: str
    updated_at: float | None = None
    updated_by: str | None = None
    tags: list[str]


class PolicyListResponse(BaseModel):
    """List of policies."""

    policies: list[PolicyResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Policy Store
# ---------------------------------------------------------------------------


class PolicyStore:
    """In-memory policy store (migrate to DB in production)."""

    def __init__(self):
        self.policies: dict[str, CompliancePolicy] = {}
        self._init_default_policies()

    def _init_default_policies(self):
        """Initialize default policies for LGPD, GDPR, AI Act."""
        # LGPD Default Policy
        lgpd_policy = CompliancePolicy(
            policy_id="policy_lgpd_default",
            name="LGPD Default Policy",
            description="Default LGPD compliance policy - Articles 7, 18, 20",
            policy_type=PolicyType.LGPD,
            version="1.0.0",
            status=PolicyStatus.ACTIVE,
            created_by="system",
            tags=["lgpd", "default", "brazil"],
            rules=[
                PolicyRule(
                    rule_id="lgpd_art7_consent",
                    name="LGPD Article 7 - Consent Required",
                    description="Data processing requires valid consent token",
                    condition={"field": "consent_token", "operator": "exists"},
                    action=PolicySeverity.BLOCK,
                    error_message="LGPD Article 7 violation: Consent token required",
                ),
                PolicyRule(
                    rule_id="lgpd_art18_access",
                    name="LGPD Article 18 - Data Access Rights",
                    description="User has right to access their data",
                    condition={"field": "action", "operator": "==", "value": "data_access"},
                    action=PolicySeverity.AUDIT,
                    error_message=None,
                ),
            ],
        )
        self.policies[lgpd_policy.policy_id] = lgpd_policy

        # GDPR Default Policy
        gdpr_policy = CompliancePolicy(
            policy_id="policy_gdpr_default",
            name="GDPR Default Policy",
            description="Default GDPR compliance policy - Articles 6, 15, 17",
            policy_type=PolicyType.GDPR,
            version="1.0.0",
            status=PolicyStatus.ACTIVE,
            created_by="system",
            tags=["gdpr", "default", "eu"],
            rules=[
                PolicyRule(
                    rule_id="gdpr_art6_lawful_basis",
                    name="GDPR Article 6 - Lawful Basis",
                    description="Processing must have lawful basis",
                    condition={
                        "field": "lawful_basis",
                        "operator": "in",
                        "value": ["consent", "contract", "legal_obligation"],
                    },
                    action=PolicySeverity.BLOCK,
                    error_message="GDPR Article 6 violation: No lawful basis for processing",
                ),
            ],
        )
        self.policies[gdpr_policy.policy_id] = gdpr_policy

        # AI Act Default Policy
        ai_act_policy = CompliancePolicy(
            policy_id="policy_ai_act_default",
            name="EU AI Act Default Policy",
            description="Default EU AI Act compliance - Articles 13, 14 (Transparency & Oversight)",
            policy_type=PolicyType.AI_ACT,
            version="1.0.0",
            status=PolicyStatus.ACTIVE,
            created_by="system",
            tags=["ai_act", "default", "eu", "high_risk"],
            rules=[
                PolicyRule(
                    rule_id="ai_act_art13_transparency",
                    name="AI Act Article 13 - Transparency",
                    description="AI decisions must be explainable",
                    condition={"field": "requires_explanation", "operator": "==", "value": True},
                    action=PolicySeverity.BLOCK,
                    error_message="AI Act Article 13 violation: Explanation required for high-risk AI",
                ),
            ],
        )
        self.policies[ai_act_policy.policy_id] = ai_act_policy

    def create_policy(
        self,
        name: str,
        description: str,
        policy_type: PolicyType,
        rules: list[PolicyRuleCreate],
        created_by: str,
        metadata: dict[str, Any] = None,
        tags: list[str] = None,
    ) -> CompliancePolicy:
        """Create a new compliance policy."""
        policy_id = f"policy_{uuid.uuid4().hex[:16]}"

        # Convert rule requests to PolicyRule objects
        policy_rules = [
            PolicyRule(
                rule_id=f"rule_{uuid.uuid4().hex[:12]}",
                name=rule.name,
                description=rule.description,
                condition=rule.condition,
                action=rule.action,
                error_message=rule.error_message,
            )
            for rule in rules
        ]

        policy = CompliancePolicy(
            policy_id=policy_id,
            name=name,
            description=description,
            policy_type=policy_type,
            version="1.0.0",
            status=PolicyStatus.DRAFT,  # Start as draft
            rules=policy_rules,
            metadata=metadata or {},
            created_by=created_by,
            tags=tags or [],
        )

        self.policies[policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> CompliancePolicy | None:
        """Get a policy by ID."""
        return self.policies.get(policy_id)

    def list_policies(
        self,
        policy_type: PolicyType | None = None,
        status: PolicyStatus | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CompliancePolicy], int]:
        """List policies with filters and pagination."""
        filtered = list(self.policies.values())

        # Apply filters
        if policy_type:
            filtered = [p for p in filtered if p.policy_type == policy_type]
        if status:
            filtered = [p for p in filtered if p.status == status]
        if tags:
            filtered = [p for p in filtered if any(tag in p.tags for tag in tags)]

        total = len(filtered)

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]

        return paginated, total

    def update_policy(
        self,
        policy_id: str,
        updated_by: str,
        name: str | None = None,
        description: str | None = None,
        status: PolicyStatus | None = None,
        rules: list[PolicyRuleCreate] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> CompliancePolicy | None:
        """Update an existing policy."""
        policy = self.policies.get(policy_id)
        if not policy:
            return None

        # Update fields
        if name:
            policy.name = name
        if description:
            policy.description = description
        if status:
            policy.status = status
        if metadata is not None:
            policy.metadata = metadata
        if tags is not None:
            policy.tags = tags

        if rules is not None:
            # Replace rules
            policy.rules = [
                PolicyRule(
                    rule_id=f"rule_{uuid.uuid4().hex[:12]}",
                    name=rule.name,
                    description=rule.description,
                    condition=rule.condition,
                    action=rule.action,
                    error_message=rule.error_message,
                )
                for rule in rules
            ]

        # Update metadata
        policy.updated_at = time.time()
        policy.updated_by = updated_by

        # Increment version on significant changes
        if rules is not None or status == PolicyStatus.ACTIVE:
            major, minor, patch = policy.version.split(".")
            policy.version = f"{major}.{int(minor) + 1}.0"

        return policy

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy (archive it)."""
        policy = self.policies.get(policy_id)
        if not policy:
            return False

        # Don't actually delete - archive instead
        policy.status = PolicyStatus.ARCHIVED
        policy.updated_at = time.time()
        return True

    def hard_delete_policy(self, policy_id: str) -> bool:
        """Permanently delete a policy (use with caution)."""
        if policy_id in self.policies:
            del self.policies[policy_id]
            return True
        return False


# Global store instance
_policy_store = PolicyStore()


def get_policy_store() -> PolicyStore:
    """Get the global policy store."""
    return _policy_store
