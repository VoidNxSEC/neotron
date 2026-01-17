"""
Compliance Auditors

Regulation-specific guardrail implementations:
- LGPD (Lei Geral de Proteção de Dados - Brazil)
- GDPR (General Data Protection Regulation - EU)
- AI Act (EU Artificial Intelligence Act)
- SOC2 (Service Organization Control 2)

Each auditor module provides pre-configured guardrails for common
compliance requirements.
"""

from neutron.compliance.auditors.lgpd import (
    lgpd_art18_explanation_guardrail,
    lgpd_art20_portability_guardrail,
    LGPD_GUARDRAILS,
    get_lgpd_guardrails,
    get_lgpd_guardrail_by_article,
    validate_with_lgpd
)

__all__ = [
    # LGPD guardrails
    "lgpd_art18_explanation_guardrail",
    "lgpd_art20_portability_guardrail",
    "LGPD_GUARDRAILS",
    "get_lgpd_guardrails",
    "get_lgpd_guardrail_by_article",
    "validate_with_lgpd",
]
