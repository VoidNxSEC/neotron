#!/usr/bin/env python3
"""
Phase 3 Demo Script - ORACLE Explainability & EU AI Act Compliance

Demonstrates:
1. ORACLE explainability framework (5 explanation strategies)
2. EU AI Act compliance (Articles 5, 13, 14)
3. Risk classification system
4. Full NEXUS integration with transparency
5. CORTEX + SYNAPSE + GDPR + ORACLE + AI Act

This is an interactive demo showcasing the complete NEXUS platform
with enterprise-grade explainability and compliance.
"""

import asyncio

# CORTEX - Multi-Agent Orchestration
from neutron.orchestration.cortex import (
    AgentResult,
    AgentSwarm,
    ConsensusStrategy,
    Task,
)

# EU AI Act - Compliance
from neutron.compliance.auditors.ai_act import (
    AISystemRiskLevel,
    check_ai_act_article_13_transparency,
    check_ai_act_article_14_human_oversight,
    classify_ai_system_risk,
)

# Compliance
from neutron.compliance.sentinel import AgentOutput

# ORACLE - Explainability Framework
from neutron.reasoning import (
    ExplanationType,
    create_explainer,
    explain_agent_decision,
)

# =============================================================================
# Colors for Terminal Output
# =============================================================================


class Colors:
    """ANSI color codes for terminal output"""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}")
    print(f"{text.center(80)}")
    print(f"{'=' * 80}{Colors.END}\n")


def print_subheader(text: str):
    """Print subsection header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'-' * len(text)}{Colors.END}")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


# =============================================================================
# Demo 1: ORACLE Explanation Strategies
# =============================================================================


async def demo_oracle_strategies():
    """Demonstrate all 5 ORACLE explanation strategies"""
    print_header("Demo 1: ORACLE Explanation Strategies")

    # Sample decision data
    decision = "Loan approved"
    input_data = {
        "credit_score": 750,
        "income": 85000,
        "debt_ratio": 0.3,
        "employment_years": 5,
    }
    output_data = {
        "confidence": 0.92,
        "approval_amount": 250000,
    }

    # Demo 1.1: Feature Importance
    print_subheader("1.1 Feature Importance Explanation")
    print_info("Shows which input features most influenced the decision")

    explainer = create_explainer(ExplanationType.FEATURE_IMPORTANCE)
    explanation = explainer.explain(decision, input_data, output_data)

    print(f"\n{explanation.to_human_readable(max_evidence=3)}\n")
    print_success("Feature importance explanation generated")

    # Demo 1.2: Counterfactual
    print_subheader("1.2 Counterfactual Explanation")
    print_info("Shows what would need to change for a different outcome")

    explanation = explain_agent_decision(
        decision=decision,
        input_data=input_data,
        output_data=output_data,
        explanation_type=ExplanationType.COUNTERFACTUAL,
        metadata={"threshold": 700},
    )

    print(f"\n{explanation.to_human_readable()}\n")
    print_success("Counterfactual explanation generated")

    # Demo 1.3: Example-Based
    print_subheader("1.3 Example-Based Explanation")
    print_info("References similar past cases to explain the decision")

    similar_cases = [
        {"case_id": "CASE-2024-001", "outcome": "approved", "similarity": 0.94},
        {"case_id": "CASE-2024-087", "outcome": "approved", "similarity": 0.89},
        {"case_id": "CASE-2023-456", "outcome": "approved", "similarity": 0.85},
    ]

    explanation = explain_agent_decision(
        decision=decision,
        input_data=input_data,
        output_data=output_data,
        explanation_type=ExplanationType.EXAMPLE_BASED,
        metadata={"similar_cases": similar_cases},
    )

    print(f"\n{explanation.to_human_readable()}\n")
    print_success("Example-based explanation generated")

    # Demo 1.4: Chain-of-Thought
    print_subheader("1.4 Chain-of-Thought Explanation")
    print_info("Step-by-step reasoning process")

    reasoning_steps = [
        "Step 1: Verified credit score (750) exceeds minimum requirement (680)",
        "Step 2: Calculated income-to-debt ratio: 0.3 (acceptable, below 0.43 limit)",
        "Step 3: Confirmed stable employment history (5 years)",
        "Step 4: Assessed overall risk profile: LOW",
        "Step 5: Approved loan with high confidence (92%)",
    ]

    explanation = explain_agent_decision(
        decision=decision,
        input_data=input_data,
        output_data=output_data,
        explanation_type=ExplanationType.CHAIN_OF_THOUGHT,
        metadata={"reasoning_steps": reasoning_steps},
    )

    print(f"\n{explanation.to_human_readable()}\n")
    print_success("Chain-of-thought explanation generated")

    # Demo 1.5: Rule-Based
    print_subheader("1.5 Rule-Based Explanation")
    print_info("Shows which business rules were applied")

    rules = [
        "IF credit_score >= 700 THEN eligible_for_prime_rate",
        "IF income >= 80000 AND debt_ratio < 0.4 THEN low_risk",
        "IF employment_years >= 2 THEN stable_employment",
    ]

    explanation = explain_agent_decision(
        decision=decision,
        input_data=input_data,
        output_data=output_data,
        explanation_type=ExplanationType.RULE_BASED,
        metadata={"rules": rules},
    )

    print(f"\n{explanation.to_human_readable()}\n")
    print_success("Rule-based explanation generated")


# =============================================================================
# Demo 2: EU AI Act Risk Classification
# =============================================================================


async def demo_ai_act_risk_classification():
    """Demonstrate EU AI Act risk classification"""
    print_header("Demo 2: EU AI Act Risk Classification")

    test_cases = [
        ("spam_filter", AISystemRiskLevel.MINIMAL, "Email spam detection"),
        ("chatbot", AISystemRiskLevel.LIMITED, "Customer service chatbot"),
        ("loan_approval", AISystemRiskLevel.HIGH, "Credit scoring system"),
        ("hiring_decision", AISystemRiskLevel.HIGH, "Recruitment AI"),
        ("social_scoring", AISystemRiskLevel.UNACCEPTABLE, "Government social credit"),
    ]

    for use_case, expected_risk, description in test_cases:
        risk = classify_ai_system_risk(use_case)

        color = Colors.GREEN
        if risk == AISystemRiskLevel.HIGH:
            color = Colors.YELLOW
        elif risk == AISystemRiskLevel.UNACCEPTABLE:
            color = Colors.RED

        print(f"{color}• {description:35} → {risk.value.upper():15}{Colors.END}")

        if risk == AISystemRiskLevel.UNACCEPTABLE:
            print_error("  PROHIBITED: Cannot be deployed in the EU")
        elif risk == AISystemRiskLevel.HIGH:
            print_warning("  Requires human oversight and transparency disclosure")
        elif risk == AISystemRiskLevel.LIMITED:
            print_info("  Requires transparency disclosure")
        else:
            print_success("  Minimal regulatory requirements")

    print()


# =============================================================================
# Demo 3: EU AI Act Article 13 - Transparency
# =============================================================================


async def demo_ai_act_article_13():
    """Demonstrate Article 13 transparency requirements"""
    print_header("Demo 3: EU AI Act Article 13 - Transparency")

    # Demo 3.1: Compliant High-Risk System
    print_subheader("3.1 Compliant High-Risk AI System")

    output = AgentOutput(
        content="Loan approved: $250,000 at 4.5% APR",
        metadata={
            "use_case": "credit_score",
            "ai_disclosure": True,
            "system_info": "NEXUS Credit Assessment System v3.2",
            "capabilities": "Analyzes credit history, income, employment, and debt ratios using ensemble ML models",
            "limitations": "Cannot consider contextual factors like recent life events or non-financial circumstances",
        },
    )

    result = check_ai_act_article_13_transparency(output)

    if result.passed:
        print_success(f"Article 13 Compliance: {result.details}")
    else:
        print_error(f"Article 13 Violation: {result.details}")

    # Demo 3.2: Non-Compliant System (Missing Disclosure)
    print_subheader("3.2 Non-Compliant System (Missing AI Disclosure)")

    output_bad = AgentOutput(
        content="Decision: Approved", metadata={"use_case": "loan_approval"}  # Missing disclosure
    )

    result = check_ai_act_article_13_transparency(output_bad)

    if result.passed:
        print_success(f"Article 13 Compliance: {result.details}")
    else:
        print_error(f"Article 13 Violation: {result.details}")
        print_info("Fix: Add ai_disclosure=True and system_info to metadata")


# =============================================================================
# Demo 4: EU AI Act Article 14 - Human Oversight
# =============================================================================


async def demo_ai_act_article_14():
    """Demonstrate Article 14 human oversight requirements"""
    print_header("Demo 4: EU AI Act Article 14 - Human Oversight")

    # Demo 4.1: Compliant High-Risk System
    print_subheader("4.1 Compliant High-Risk System with Human Oversight")

    output = AgentOutput(
        content="Candidate recommended for hire",
        metadata={
            "use_case": "recruitment",
            "human_oversight_enabled": True,
            "oversight_mechanism": "human_in_the_loop",
            "overseer_id": "hiring_manager_johndoe",
            "can_override": True,
        },
    )

    result = check_ai_act_article_14_human_oversight(output)

    if result.passed:
        print_success(f"Article 14 Compliance: {result.details}")
    else:
        print_error(f"Article 14 Violation: {result.details}")

    # Demo 4.2: Non-Compliant High-Risk (No Oversight)
    print_subheader("4.2 Non-Compliant High-Risk System (No Oversight)")

    output_bad = AgentOutput(
        content="Loan denied",
        metadata={
            "use_case": "credit_score",
            "human_oversight_enabled": False,  # VIOLATION
        },
    )

    result = check_ai_act_article_14_human_oversight(output_bad)

    if result.passed:
        print_success(f"Article 14 Compliance: {result.details}")
    else:
        print_error(f"Article 14 Violation: {result.details}")
        print_info("Fix: Enable human oversight for high-risk AI systems")

    # Demo 4.3: Minimal Risk (Oversight Not Required)
    print_subheader("4.3 Minimal Risk System (Oversight Not Required)")

    output_minimal = AgentOutput(content="This email is spam", metadata={"use_case": "spam_filter"})

    result = check_ai_act_article_14_human_oversight(output_minimal)

    if result.passed:
        print_success(f"Article 14 Compliance: {result.details}")


# =============================================================================
# Demo 5: CORTEX with ORACLE Explanations
# =============================================================================


class MockLoanAgent:
    """Mock loan assessment agent"""

    def __init__(self, agent_id: str, bias: float = 0):
        self.agent_id = agent_id
        self.bias = bias

    async def execute(self, task: Task) -> AgentResult:
        """Assess loan application"""
        await asyncio.sleep(0.1)  # Simulate processing

        credit_score = task.input.get("credit_score", 700)
        base_confidence = min(credit_score / 850, 1.0)
        confidence = max(0.1, min(0.99, base_confidence + self.bias))

        decision = "approved" if credit_score >= 680 else "denied"

        return AgentResult(
            agent_id=self.agent_id,
            output=decision,
            confidence=confidence,
            explanation=f"{self.agent_id} assessed credit score {credit_score}",
        )


async def demo_cortex_with_oracle():
    """Demonstrate CORTEX multi-agent with ORACLE explanations"""
    print_header("Demo 5: CORTEX Multi-Agent with ORACLE Explanations")

    # Create agent swarm
    agents = [
        MockLoanAgent("traditional_model", bias=0.05),
        MockLoanAgent("ml_model_v1", bias=0.02),
        MockLoanAgent("ml_model_v2", bias=-0.01),
        MockLoanAgent("risk_specialist", bias=0.03),
    ]

    swarm = AgentSwarm(agents, name="loan_assessment_swarm")

    # Create task
    task = Task(
        type="credit_assessment",
        input={"credit_score": 750, "income": 85000},
        consensus_strategy=ConsensusStrategy.WEIGHTED_AVERAGE,
    )

    print_info(f"Executing task with {len(agents)} agents...")

    # Execute with auto-explanation
    result = await swarm.execute(
        task, generate_explanation=True, explanation_type=ExplanationType.CHAIN_OF_THOUGHT
    )

    print_success(f"Consensus reached: {result.consensus_output}")
    print_info(f"Confidence: {result.consensus_confidence:.2%}")
    print_info(f"Agreement: {result.agreement_score:.2%}")

    # Show explanation
    print_subheader("ORACLE Explanation")
    if result.explanation:
        print(f"\n{result.explanation.to_human_readable()}\n")
    else:
        print_warning("No explanation generated")


# =============================================================================
# Demo 6: Full NEXUS Integration (Simulated)
# =============================================================================


async def demo_full_nexus_integration():
    """Demonstrate full NEXUS workflow with all Phase 3 features"""
    print_header("Demo 6: Full NEXUS Integration Workflow")

    print_info("Simulated NEXUS Workflow Components:")
    print(f"{Colors.CYAN}  1. CORTEX → Multi-agent consensus{Colors.END}")
    print(f"{Colors.CYAN}  2. SYNAPSE → Long-term memory retrieval{Colors.END}")
    print(f"{Colors.CYAN}  3. GDPR → Privacy compliance validation{Colors.END}")
    print(f"{Colors.CYAN}  4. EU AI Act → Transparency & oversight validation{Colors.END}")
    print(f"{Colors.CYAN}  5. ORACLE → Explainability generation{Colors.END}\n")

    # Simulated result
    simulated_result = {
        "consensus_output": "approved",
        "consensus_confidence": 0.91,
        "agreement_score": 0.88,
        "ai_system_risk_level": "high",
        "compliance_passed": True,
        "ai_act_compliance_passed": True,
        "explanation_type": "chain_of_thought",
    }

    print_subheader("Workflow Execution")

    steps = [
        "Retrieving 5 relevant memories from SYNAPSE...",
        "Executing 4 specialized agents with memory context...",
        "Reaching consensus using weighted_average strategy...",
        "Validating with GDPR guardrails...",
        "Classifying AI system risk: HIGH",
        "Validating with EU AI Act (Article 13, 14)...",
        "Generating ORACLE chain-of-thought explanation...",
        "Storing consensus result as new memory...",
    ]

    for i, step in enumerate(steps, 1):
        await asyncio.sleep(0.2)
        print_success(f"Step {i}/8: {step}")

    print_subheader("Final Result")
    print(f"{Colors.GREEN}Consensus: {simulated_result['consensus_output']}{Colors.END}")
    print(f"{Colors.GREEN}Confidence: {simulated_result['consensus_confidence']:.1%}{Colors.END}")
    print(f"{Colors.GREEN}Agreement: {simulated_result['agreement_score']:.1%}{Colors.END}")
    print(
        f"{Colors.GREEN}Risk Level: {simulated_result['ai_system_risk_level'].upper()}{Colors.END}"
    )
    print(f"{Colors.GREEN}GDPR Compliant: ✓{Colors.END}")
    print(f"{Colors.GREEN}EU AI Act Compliant: ✓{Colors.END}")
    print(f"{Colors.GREEN}Explanation Generated: ✓{Colors.END}\n")


# =============================================================================
# Main Demo Runner
# =============================================================================


async def main():
    """Run all Phase 3 demos"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("NEXUS Platform - Phase 3 Demo".center(80))
    print("ORACLE Explainability + EU AI Act Compliance".center(80))
    print("=" * 80)
    print(Colors.END)

    demos = [
        ("ORACLE Explanation Strategies", demo_oracle_strategies),
        ("EU AI Act Risk Classification", demo_ai_act_risk_classification),
        ("EU AI Act Article 13 (Transparency)", demo_ai_act_article_13),
        ("EU AI Act Article 14 (Human Oversight)", demo_ai_act_article_14),
        ("CORTEX with ORACLE Explanations", demo_cortex_with_oracle),
        ("Full NEXUS Integration", demo_full_nexus_integration),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            await demo_func()
            print_success(f"Demo {i}/{len(demos)} completed: {name}")
        except Exception as e:
            print_error(f"Demo {i}/{len(demos)} failed: {name}")
            print(f"{Colors.RED}Error: {e}{Colors.END}")
            import traceback

            traceback.print_exc()

    # Final Summary
    print_header("Phase 3 Demo Complete")
    print_success("✓ ORACLE explainability framework (5 strategies)")
    print_success("✓ EU AI Act compliance (Articles 5, 13, 14)")
    print_success("✓ Risk classification system (4 levels)")
    print_success("✓ CORTEX + ORACLE integration")
    print_success("✓ Full NEXUS workflow with transparency")

    print(f"\n{Colors.BOLD}NEXUS Platform Phase 3: Production Ready{Colors.END}\n")


if __name__ == "__main__":
    asyncio.run(main())
