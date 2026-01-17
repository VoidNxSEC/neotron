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

from neutron.compliance.auditors.ai_act import (
    ARTICLE_5_PROHIBITED_PRACTICES,
    ARTICLE_13_TRANSPARENCY,
    ARTICLE_14_HUMAN_OVERSIGHT,
    AISystemRiskLevel,
    check_ai_act_article_13_transparency,
    check_ai_act_article_14_human_oversight,
    check_ai_act_prohibited_practices,
    classify_ai_system_risk,
    get_ai_act_guardrails,
    validate_ai_act_compliance,
)
from neutron.compliance.auditors.gdpr import (
    GDPR_GUARDRAILS,
    GDPRErasureHandler,
    gdpr_art15_data_access_guardrail,
    gdpr_art17_erasure_support_guardrail,
    gdpr_art22_human_oversight_guardrail,
    get_gdpr_guardrail_by_article,
    get_gdpr_guardrails,
    validate_with_gdpr,
)
from neutron.compliance.auditors.lgpd import (
    LGPD_GUARDRAILS,
    get_lgpd_guardrail_by_article,
    get_lgpd_guardrails,
    lgpd_art18_explanation_guardrail,
    lgpd_art20_portability_guardrail,
    validate_with_lgpd,
)

__all__ = [
    # LGPD guardrails
    "lgpd_art18_explanation_guardrail",
    "lgpd_art20_portability_guardrail",
    "LGPD_GUARDRAILS",
    "get_lgpd_guardrails",
    "get_lgpd_guardrail_by_article",
    "validate_with_lgpd",
    # GDPR guardrails
    "gdpr_art22_human_oversight_guardrail",
    "gdpr_art15_data_access_guardrail",
    "gdpr_art17_erasure_support_guardrail",
    "GDPR_GUARDRAILS",
    "get_gdpr_guardrails",
    "get_gdpr_guardrail_by_article",
    "validate_with_gdpr",
    "GDPRErasureHandler",
    # EU AI Act guardrails
    "AISystemRiskLevel",
    "classify_ai_system_risk",
    "check_ai_act_article_13_transparency",
    "check_ai_act_article_14_human_oversight",
    "check_ai_act_prohibited_practices",
    "ARTICLE_13_TRANSPARENCY",
    "ARTICLE_14_HUMAN_OVERSIGHT",
    "ARTICLE_5_PROHIBITED_PRACTICES",
    "get_ai_act_guardrails",
    "validate_ai_act_compliance",
]
