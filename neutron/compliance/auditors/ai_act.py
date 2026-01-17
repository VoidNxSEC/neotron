"""
EU AI Act Compliance Auditors

European Union Artificial Intelligence Act (EU AI Act)

This module implements EU AI Act-specific compliance guardrails for AI agent outputs.

Key EU AI Act Articles Implemented:
- Article 13: Transparency and information provision for users
- Article 14: Human oversight for high-risk AI systems
- Annex III: Risk classification (minimal, limited, high-risk, unacceptable)

The EU AI Act is the world's first comprehensive AI regulation, establishing
risk-based requirements for AI systems operating in the EU.

Reference: https://artificialintelligenceact.eu/
"""

from enum import Enum
from typing import Any

from neutron.compliance.sentinel import (
    AgentOutput,
    ComplianceGuardrail,
    ValidationResult,
    create_guardrail,
)

# =============================================================================
# Risk Classification System (Based on EU AI Act Annex III)
# =============================================================================


class AISystemRiskLevel(Enum):
    """
    EU AI Act risk classification levels

    Based on Annex III of the EU AI Act, AI systems are classified by risk level:
    - UNACCEPTABLE: Prohibited AI practices (social scoring, real-time biometric surveillance)
    - HIGH: AI systems in critical areas (employment, credit scoring, law enforcement)
    - LIMITED: AI systems requiring transparency (chatbots, deepfakes)
    - MINIMAL: All other AI systems with minimal regulatory requirements
    """

    UNACCEPTABLE = "unacceptable"  # Prohibited practices
    HIGH = "high"  # High-risk AI systems (Annex III)
    LIMITED = "limited"  # Limited risk (transparency obligations)
    MINIMAL = "minimal"  # Minimal risk (voluntary codes)


def classify_ai_system_risk(
    use_case: str, metadata: dict[str, Any] | None = None
) -> AISystemRiskLevel:
    """
    Classify AI system risk level according to EU AI Act Annex III

    High-risk AI systems (Annex III) include:
    - Biometric identification and categorization
    - Critical infrastructure management
    - Education and vocational training
    - Employment and worker management
    - Access to essential services (credit, insurance, etc.)
    - Law enforcement
    - Migration and border control
    - Justice and democratic processes

    Args:
        use_case: Description of the AI system use case
        metadata: Optional metadata with additional context

    Returns:
        AISystemRiskLevel classification

    Example:
        >>> risk = classify_ai_system_risk(
        ...     use_case="loan_approval",
        ...     metadata={"sector": "financial_services"}
        ... )
        >>> assert risk == AISystemRiskLevel.HIGH
    """
    use_case_lower = use_case.lower()
    metadata = metadata or {}

    # Check for unacceptable risk (prohibited practices)
    unacceptable_keywords = [
        "social_scoring",
        "social_credit",
        "real_time_biometric_surveillance",
        "subliminal_manipulation",
        "exploit_vulnerabilities",
    ]
    if any(keyword in use_case_lower for keyword in unacceptable_keywords):
        return AISystemRiskLevel.UNACCEPTABLE

    # Check for high-risk use cases (Annex III)
    high_risk_keywords = [
        # Biometric systems
        "biometric",
        "facial_recognition",
        "emotion_recognition",
        # Critical infrastructure
        "critical_infrastructure",
        "water_supply",
        "gas_supply",
        "electricity",
        # Education
        "education",
        "exam_scoring",
        "admission",
        "student_evaluation",
        # Employment
        "employment",
        "recruitment",
        "hiring",
        "job_application",
        "worker_performance",
        "promotion",
        "termination",
        # Essential services
        "credit",
        "loan",
        "creditworthiness",
        "credit_score",
        "insurance",
        "risk_assessment",
        "emergency_services",
        # Law enforcement
        "law_enforcement",
        "crime_prediction",
        "risk_profiling",
        "polygraph",
        "evidence_evaluation",
        # Migration
        "asylum",
        "visa",
        "border_control",
        "immigration",
        # Justice
        "legal_decision",
        "court",
        "judicial",
    ]
    if any(keyword in use_case_lower for keyword in high_risk_keywords):
        return AISystemRiskLevel.HIGH

    # Check for limited risk (transparency requirements)
    limited_risk_keywords = [
        "chatbot",
        "conversational_ai",
        "deepfake",
        "synthetic_media",
        "content_generation",
        "recommendation",
    ]
    if any(keyword in use_case_lower for keyword in limited_risk_keywords):
        return AISystemRiskLevel.LIMITED

    # Default to minimal risk
    return AISystemRiskLevel.MINIMAL


# =============================================================================
# Article 13 - Transparency and Information Provision
# =============================================================================


def check_ai_act_article_13_transparency(output: AgentOutput) -> ValidationResult:
    """
    EU AI Act Article 13: Transparency obligations for certain AI systems

    Article 13 requires that:
    1. Users are informed they are interacting with an AI system
    2. AI-generated content is labeled appropriately
    3. Users can access information about the AI system's capabilities and limitations
    4. High-risk AI systems provide clear information to deployers and users

    This check ensures AI outputs include required transparency information.

    Requirements:
    - Must have 'ai_disclosure' flag set to True
    - Must include 'system_info' describing the AI system
    - For high-risk systems, must include 'capabilities' and 'limitations'
    - For synthetic content, must include 'synthetic_content_warning'

    Args:
        output: Agent output to validate

    Returns:
        ValidationResult indicating Article 13 compliance

    Example:
        >>> output = AgentOutput(
        ...     content="Loan approved",
        ...     metadata={
        ...         "ai_disclosure": True,
        ...         "system_info": "AI credit assessment system",
        ...         "capabilities": "Evaluates creditworthiness",
        ...         "limitations": "May not account for recent events"
        ...     }
        ... )
        >>> result = check_ai_act_article_13_transparency(output)
        >>> assert result.passed
    """
    if not output.metadata:
        return ValidationResult(
            passed=False,
            details=(
                "EU AI Act Article 13 violation: No metadata provided. "
                "AI systems must disclose their nature to users."
            ),
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 13",
                "requirement": "transparency",
                "violation_type": "missing_metadata",
            },
        )

    # Check AI disclosure
    ai_disclosure = output.metadata.get("ai_disclosure", False)
    if not ai_disclosure:
        return ValidationResult(
            passed=False,
            details=(
                "EU AI Act Article 13 violation: AI system must disclose its nature. "
                "Set metadata['ai_disclosure'] = True and provide system information."
            ),
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 13",
                "requirement": "ai_disclosure",
                "violation_type": "missing_disclosure",
            },
        )

    # Check system information
    system_info = output.metadata.get("system_info")
    if not system_info:
        return ValidationResult(
            passed=False,
            details=(
                "EU AI Act Article 13 violation: Must provide AI system information. "
                "Set metadata['system_info'] with system description."
            ),
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 13",
                "requirement": "system_information",
                "violation_type": "missing_system_info",
            },
        )

    # For high-risk systems, require capabilities and limitations
    use_case = output.metadata.get("use_case", "")
    risk_level = classify_ai_system_risk(use_case, output.metadata)

    if risk_level == AISystemRiskLevel.HIGH:
        capabilities = output.metadata.get("capabilities")
        limitations = output.metadata.get("limitations")

        if not capabilities:
            return ValidationResult(
                passed=False,
                details=(
                    "EU AI Act Article 13 violation: High-risk AI systems must "
                    "disclose their capabilities. Set metadata['capabilities']."
                ),
                confidence=1.0,
                metadata={
                    "article": "EU AI Act Article 13",
                    "requirement": "capabilities_disclosure",
                    "violation_type": "missing_capabilities",
                    "risk_level": risk_level.value,
                },
            )

        if not limitations:
            return ValidationResult(
                passed=False,
                details=(
                    "EU AI Act Article 13 violation: High-risk AI systems must "
                    "disclose their limitations. Set metadata['limitations']."
                ),
                confidence=1.0,
                metadata={
                    "article": "EU AI Act Article 13",
                    "requirement": "limitations_disclosure",
                    "violation_type": "missing_limitations",
                    "risk_level": risk_level.value,
                },
            )

    # Check for synthetic content warning (deepfakes, generated content)
    is_synthetic = output.metadata.get("synthetic_content", False)
    if is_synthetic:
        synthetic_warning = output.metadata.get("synthetic_content_warning")
        if not synthetic_warning:
            return ValidationResult(
                passed=False,
                details=(
                    "EU AI Act Article 13 violation: AI-generated or manipulated content "
                    "must include clear warning. Set metadata['synthetic_content_warning']."
                ),
                confidence=1.0,
                metadata={
                    "article": "EU AI Act Article 13",
                    "requirement": "synthetic_content_labeling",
                    "violation_type": "missing_synthetic_warning",
                },
            )

    # All transparency requirements met
    return ValidationResult(
        passed=True,
        details=f"EU AI Act Article 13 compliant: Transparency requirements met ({risk_level.value} risk)",
        confidence=1.0,
        metadata={
            "article": "EU AI Act Article 13",
            "risk_level": risk_level.value,
            "disclosure_complete": True,
        },
    )


# =============================================================================
# Article 14 - Human Oversight
# =============================================================================


def check_ai_act_article_14_human_oversight(output: AgentOutput) -> ValidationResult:
    """
    EU AI Act Article 14: Human oversight for high-risk AI systems

    Article 14 requires that high-risk AI systems are designed and developed
    in such a way that they can be effectively overseen by natural persons.

    Human oversight measures must enable individuals to:
    1. Fully understand the capacities and limitations of the AI system
    2. Remain aware of possible automation bias
    3. Interpret the AI system's output correctly
    4. Decide not to use or override the AI system's output
    5. Interrupt the system through a "stop" button or similar

    Requirements for high-risk systems:
    - Must have 'human_oversight_enabled' flag
    - Must include 'oversight_mechanism' (e.g., "human_in_the_loop")
    - Must have 'overseer_id' identifying the human overseer
    - Must have 'can_override' flag set to True
    - For critical decisions, must have 'human_decision_authority'

    Args:
        output: Agent output to validate

    Returns:
        ValidationResult indicating Article 14 compliance
    """
    if not output.metadata:
        return ValidationResult(
            passed=False,
            details=(
                "EU AI Act Article 14 violation: No metadata provided. "
                "Cannot determine oversight requirements."
            ),
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 14",
                "requirement": "metadata_presence",
                "violation_type": "missing_metadata",
            },
        )

    # Classify risk level
    use_case = output.metadata.get("use_case", "")
    risk_level = classify_ai_system_risk(use_case, output.metadata)

    # Only high-risk systems require Article 14 oversight
    if risk_level != AISystemRiskLevel.HIGH:
        return ValidationResult(
            passed=True,
            details=f"EU AI Act Article 14 compliant: {risk_level.value} risk system - oversight not required",
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 14",
                "risk_level": risk_level.value,
                "oversight_required": False,
            },
        )

    # HIGH-RISK SYSTEMS: Check oversight requirements

    # Check oversight enabled
    oversight_enabled = output.metadata.get("human_oversight_enabled", False)
    if not oversight_enabled:
        return ValidationResult(
            passed=False,
            details=(
                "EU AI Act Article 14 violation: High-risk AI system requires human oversight. "
                "Set metadata['human_oversight_enabled'] = True."
            ),
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 14",
                "requirement": "oversight_enabled",
                "violation_type": "oversight_disabled",
                "risk_level": risk_level.value,
            },
        )

    # Check oversight mechanism
    oversight_mechanism = output.metadata.get("oversight_mechanism")
    valid_mechanisms = [
        "human_in_the_loop",  # Human reviews each decision
        "human_on_the_loop",  # Human monitors and can intervene
        "human_in_command",  # Human makes final decision
    ]

    if oversight_mechanism not in valid_mechanisms:
        return ValidationResult(
            passed=False,
            details=(
                f"EU AI Act Article 14 violation: Invalid or missing oversight mechanism. "
                f"Set metadata['oversight_mechanism'] to one of: {valid_mechanisms}"
            ),
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 14",
                "requirement": "oversight_mechanism",
                "violation_type": "invalid_mechanism",
                "risk_level": risk_level.value,
            },
        )

    # Check overseer identification
    overseer_id = output.metadata.get("overseer_id")
    if not overseer_id:
        return ValidationResult(
            passed=False,
            details=(
                "EU AI Act Article 14 violation: Human overseer must be identified. "
                "Set metadata['overseer_id'] with responsible person's ID."
            ),
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 14",
                "requirement": "overseer_identification",
                "violation_type": "missing_overseer_id",
                "risk_level": risk_level.value,
            },
        )

    # Check override capability
    can_override = output.metadata.get("can_override", False)
    if not can_override:
        return ValidationResult(
            passed=False,
            details=(
                "EU AI Act Article 14 violation: Humans must be able to override AI decisions. "
                "Set metadata['can_override'] = True."
            ),
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 14",
                "requirement": "override_capability",
                "violation_type": "override_disabled",
                "risk_level": risk_level.value,
            },
        )

    # For human-in-command, verify human has decision authority
    if oversight_mechanism == "human_in_command":
        human_decision_authority = output.metadata.get("human_decision_authority", False)
        if not human_decision_authority:
            return ValidationResult(
                passed=False,
                details=(
                    "EU AI Act Article 14 violation: 'human_in_command' mechanism requires "
                    "human decision authority. Set metadata['human_decision_authority'] = True."
                ),
                confidence=1.0,
                metadata={
                    "article": "EU AI Act Article 14",
                    "requirement": "human_decision_authority",
                    "violation_type": "missing_decision_authority",
                    "risk_level": risk_level.value,
                },
            )

    # All oversight requirements met
    return ValidationResult(
        passed=True,
        details=f"EU AI Act Article 14 compliant: Human oversight active ({oversight_mechanism})",
        confidence=1.0,
        metadata={
            "article": "EU AI Act Article 14",
            "risk_level": risk_level.value,
            "oversight_mechanism": oversight_mechanism,
            "overseer_id": overseer_id,
        },
    )


# =============================================================================
# Unacceptable Risk Check (Prohibited Practices)
# =============================================================================


def check_ai_act_prohibited_practices(output: AgentOutput) -> ValidationResult:
    """
    EU AI Act: Check for prohibited AI practices (Unacceptable Risk)

    Article 5 of the EU AI Act prohibits certain AI practices:
    1. Social scoring by governments
    2. Real-time biometric identification in public spaces (law enforcement)
    3. Subliminal manipulation causing harm
    4. Exploiting vulnerabilities of specific groups

    These practices are BANNED and will result in BLOCKING validation.

    Args:
        output: Agent output to validate

    Returns:
        ValidationResult with BLOCKING severity if prohibited practice detected
    """
    if not output.metadata:
        # Cannot determine - allow but warn
        return ValidationResult(
            passed=True,
            details="EU AI Act: Cannot verify prohibited practices without metadata",
            confidence=0.5,
            metadata={"article": "EU AI Act Article 5", "warning": "metadata_missing"},
        )

    use_case = output.metadata.get("use_case", "")
    risk_level = classify_ai_system_risk(use_case, output.metadata)

    if risk_level == AISystemRiskLevel.UNACCEPTABLE:
        return ValidationResult(
            passed=False,
            details=(
                f"EU AI Act VIOLATION: Prohibited AI practice detected. "
                f"Use case '{use_case}' is classified as UNACCEPTABLE RISK and is BANNED under Article 5. "
                f"This AI system cannot be deployed in the EU."
            ),
            confidence=1.0,
            metadata={
                "article": "EU AI Act Article 5",
                "violation_type": "prohibited_practice",
                "risk_level": "unacceptable",
                "use_case": use_case,
                "severity": "BLOCKING",
            },
        )

    return ValidationResult(
        passed=True,
        details=f"EU AI Act Article 5 compliant: No prohibited practices ({risk_level.value} risk)",
        confidence=1.0,
        metadata={"article": "EU AI Act Article 5", "risk_level": risk_level.value},
    )


# =============================================================================
# Pre-configured Guardrails
# =============================================================================

# Article 13 - Transparency (WARNING severity)
# All AI systems must be transparent about their nature
ARTICLE_13_TRANSPARENCY = create_guardrail(
    name="EU_AI_Act_Article_13_Transparency",
    check_function=check_ai_act_article_13_transparency,
    severity="WARNING",  # Warning - transparency is important but not blocking
    description=(
        "EU AI Act Article 13: Ensures AI systems provide transparency "
        "information to users about capabilities, limitations, and AI nature"
    ),
)

# Article 14 - Human Oversight (BLOCKING severity for high-risk)
# High-risk AI systems MUST have human oversight
ARTICLE_14_HUMAN_OVERSIGHT = create_guardrail(
    name="EU_AI_Act_Article_14_Human_Oversight",
    check_function=check_ai_act_article_14_human_oversight,
    severity="BLOCKING",  # Blocking - human oversight is mandatory for high-risk systems
    description=(
        "EU AI Act Article 14: Ensures high-risk AI systems have effective "
        "human oversight with override capabilities"
    ),
)

# Article 5 - Prohibited Practices (BLOCKING severity)
# Unacceptable risk AI is completely banned
ARTICLE_5_PROHIBITED_PRACTICES = create_guardrail(
    name="EU_AI_Act_Article_5_Prohibited_Practices",
    check_function=check_ai_act_prohibited_practices,
    severity="BLOCKING",  # Blocking - prohibited practices are banned
    description=(
        "EU AI Act Article 5: Blocks prohibited AI practices including "
        "social scoring, subliminal manipulation, and vulnerability exploitation"
    ),
)


# =============================================================================
# Convenience Functions
# =============================================================================


def validate_ai_act_compliance(output: AgentOutput) -> list[ValidationResult]:
    """
    Validate output against all EU AI Act requirements

    Checks:
    - Article 5: Prohibited practices (BLOCKING)
    - Article 13: Transparency (WARNING)
    - Article 14: Human oversight (BLOCKING for high-risk)

    Args:
        output: Agent output to validate

    Returns:
        List of ValidationResult for each check

    Example:
        >>> output = AgentOutput(content="Decision", metadata={...})
        >>> results = validate_ai_act_compliance(output)
        >>> all_passed = all(r.passed for r in results)
    """
    return [
        check_ai_act_prohibited_practices(output),
        check_ai_act_article_13_transparency(output),
        check_ai_act_article_14_human_oversight(output),
    ]


def get_ai_act_guardrails() -> list[ComplianceGuardrail]:
    """
    Get all EU AI Act compliance guardrails

    Returns:
        List of ComplianceGuardrail instances for EU AI Act

    Example:
        >>> from neutron.compliance.sentinel import ComplianceEngine
        >>> guardrails = get_ai_act_guardrails()
        >>> engine = ComplianceEngine(guardrails)
    """
    return [
        ARTICLE_5_PROHIBITED_PRACTICES,
        ARTICLE_13_TRANSPARENCY,
        ARTICLE_14_HUMAN_OVERSIGHT,
    ]
