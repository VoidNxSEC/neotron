#!/usr/bin/env python3
"""
SENTINEL Compliance Demo

Demonstrates LGPD Article 18 & 20 enforcement in action:
1. Non-compliant output gets blocked
2. Compliant output passes through
3. All events logged to immutable audit trail
4. Audit trail queryable for compliance reporting

Usage:
    python scripts/demo_sentinel.py
    python scripts/demo_sentinel.py --verbose
    python scripts/demo_sentinel.py --demo article18
    python scripts/demo_sentinel.py --demo article20
    python scripts/demo_sentinel.py --demo all
"""

import argparse
import sys

# Add parent directory to path for imports
sys.path.insert(0, ".")

from neutron.compliance.audit_logger import AuditLogger

from neutron.compliance.auditors import (
    lgpd_art18_explanation_guardrail,
    lgpd_art20_portability_guardrail,
)
from neutron.compliance.sentinel import AgentOutput, ComplianceViolation

# =============================================================================
# Demo Scenarios
# =============================================================================


def print_header(title: str):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_success(message: str):
    """Print success message"""
    print(f"✅ {message}")


def print_error(message: str):
    """Print error message"""
    print(f"❌ {message}")


def print_info(message: str, indent: int = 0):
    """Print info message"""
    prefix = "   " * indent
    print(f"{prefix}ℹ️  {message}")


def demo_article18_non_compliant():
    """
    Demo 1: Non-compliant output (missing explanation) gets BLOCKED

    This demonstrates LGPD Article 18 enforcement.
    """
    print_header("DEMO 1: Article 18 - Non-Compliant Output (BLOCKED)")

    print("Scenario: Agent generates loan decision without explanation")
    print("Expected: SENTINEL blocks output due to LGPD Article 18 violation\n")

    # Create non-compliant output
    output = AgentOutput(
        content="Loan application denied",
        has_explanation=False,
        explanation=None,
        explanation_quality=0.0,
        model_name="loan-decision-v1",
    )

    print(f"Agent Output: '{output.content}'")
    print(f"Has Explanation: {output.has_explanation}")
    print(f"Explanation Quality: {output.explanation_quality}\n")

    # Try to enforce
    try:
        lgpd_art18_explanation_guardrail.enforce(output)
        print_error("UNEXPECTED: Output should have been blocked!")
        return False
    except ComplianceViolation as e:
        print_success(f"Output BLOCKED by: {e.guardrail.name}")
        print_info(f"Regulation: {e.guardrail.regulation}")
        print_info(f"Severity: {e.guardrail.severity}")
        print_info(f"Reason: {e.result.details}")
        print_info(f"Confidence: {e.result.confidence:.2f}")
        print()
        print("⚡ Agent must regenerate output with adequate explanation")
        return True


def demo_article18_compliant():
    """
    Demo 2: Compliant output (with explanation) PASSES

    This demonstrates proper LGPD Article 18 compliance.
    """
    print_header("DEMO 2: Article 18 - Compliant Output (PASSED)")

    print("Scenario: Agent regenerates decision with detailed explanation")
    print("Expected: SENTINEL validates and allows output through\n")

    # Create compliant output
    output = AgentOutput(
        content="Loan application approved: $50,000 at 5.2% APR for 36 months",
        has_explanation=True,
        explanation=(
            "Loan approved based on the following criteria: "
            "Credit score of 780 (excellent range), "
            "annual income of $85,000 (sufficient), "
            "debt-to-income ratio of 22% (low risk), "
            "no late payments in past 24 months, "
            "8 years of credit history (established), "
            "and employment stability (5 years same employer)."
        ),
        explanation_quality=0.88,
        model_name="loan-decision-v1",
    )

    print(f"Agent Output: '{output.content}'")
    print(f"Has Explanation: {output.has_explanation}")
    print(f"Explanation Quality: {output.explanation_quality}")
    print(f"Explanation: {output.explanation[:80]}...\n")

    # Enforce
    try:
        enforced = lgpd_art18_explanation_guardrail.enforce(output)
        print_success(f"Output PASSED: {enforced.guardrail_name}")
        print_info(f"Validation: {enforced.validation_result.details}")
        print_info(f"Audit ID: {enforced.audit_id}")
        print_info("Logged to immutable audit trail")
        print()
        print("✨ Output approved for delivery to customer")
        return True
    except ComplianceViolation as e:
        print_error("UNEXPECTED: Output should have passed!")
        print_error(f"Reason: {e.result.details}")
        return False


def demo_article20_non_compliant():
    """
    Demo 3: Non-compliant portability (WARNING only, doesn't block)

    This demonstrates LGPD Article 20 warning-level enforcement.
    """
    print_header("DEMO 3: Article 20 - Non-Compliant Portability (WARNING)")

    print("Scenario: Agent output without exportable format specified")
    print("Expected: SENTINEL logs warning but allows output (warn severity)\n")

    # Create output without portability metadata
    output = AgentOutput(
        content="Customer risk assessment: HIGH (probability: 0.72)",
        has_explanation=True,
        explanation=(
            "High risk assessment based on: "
            "5 support tickets in last month, "
            "40% decrease in usage vs 3 months ago, "
            "1 late payment, and 18 month tenure."
        ),
        explanation_quality=0.82,
        metadata=None,  # Missing portability info
        model_name="risk-assessment-v2",
    )

    print(f"Agent Output: '{output.content}'")
    print(f"Metadata: {output.metadata}\n")

    # Enforce Article 20
    enforced = lgpd_art20_portability_guardrail.enforce(output)

    if enforced.validation_result.passed:
        print_error("UNEXPECTED: Should have failed Article 20 validation")
        return False
    else:
        print("⚠️  WARNING: Article 20 violation detected")
        print_info(f"Guardrail: {enforced.guardrail_name}")
        print_info(f"Severity: {lgpd_art20_portability_guardrail.severity}")
        print_info(f"Issue: {enforced.validation_result.details}")
        print_info(f"Audit ID: {enforced.audit_id}")
        print()
        print("ℹ️  Output NOT blocked (warning level only)")
        print("   Violation logged for compliance team review")
        return True


def demo_article20_compliant():
    """
    Demo 4: Compliant portability PASSES

    This demonstrates proper LGPD Article 20 compliance.
    """
    print_header("DEMO 4: Article 20 - Compliant Portability (PASSED)")

    print("Scenario: Agent output with proper exportable format")
    print("Expected: SENTINEL validates data portability requirements\n")

    # Create compliant output with portability metadata
    output = AgentOutput(
        content='{"customer_id": "12345", "risk_score": 0.72, "risk_level": "HIGH"}',
        has_explanation=True,
        explanation="Risk score calculated from customer behavior metrics.",
        explanation_quality=0.75,
        metadata={
            "exportable_format": "json",
            "data_structure": {
                "customer_id": "string",
                "risk_score": "float (0.0-1.0)",
                "risk_level": "string (LOW|MEDIUM|HIGH)",
            },
        },
        model_name="risk-assessment-v2",
    )

    print(f"Agent Output: {output.content}")
    print(f"Exportable Format: {output.metadata['exportable_format']}")
    print(f"Data Structure: {output.metadata['data_structure']}\n")

    # Enforce Article 20
    enforced = lgpd_art20_portability_guardrail.enforce(output)

    if enforced.validation_result.passed:
        print_success(f"Output PASSED: {enforced.guardrail_name}")
        print_info(f"Validation: {enforced.validation_result.details}")
        print_info(f"Audit ID: {enforced.audit_id}")
        print()
        print("✨ Data is portable and can be exported to other services")
        return True
    else:
        print_error("UNEXPECTED: Should have passed!")
        return False


def demo_batch_validation():
    """
    Demo 5: Batch validation of multiple outputs

    This demonstrates validating ensemble or multi-agent outputs.
    """
    print_header("DEMO 5: Batch Validation - Ensemble Models")

    print("Scenario: 3 models in ensemble, validate all outputs")
    print("Expected: Identify which models are compliant\n")

    # Create ensemble outputs
    outputs = [
        AgentOutput(
            content="Model A prediction: Approve",
            has_explanation=True,
            explanation="Approved based on strong credit score and stable income.",
            explanation_quality=0.85,
            model_name="model-a",
        ),
        AgentOutput(
            content="Model B prediction: Deny",
            has_explanation=False,  # Non-compliant
            explanation=None,
            explanation_quality=0.0,
            model_name="model-b",
        ),
        AgentOutput(
            content="Model C prediction: Approve",
            has_explanation=True,
            explanation="Approved due to low debt-to-income ratio and excellent payment history.",
            explanation_quality=0.90,
            model_name="model-c",
        ),
    ]

    # Validate each
    results = []
    for i, output in enumerate(outputs, 1):
        print(f"Model {i} ({output.model_name}):")
        print(f"  Output: {output.content}")
        print(f"  Has Explanation: {output.has_explanation}")

        try:
            enforced = lgpd_art18_explanation_guardrail.enforce(output)
            print_success("  PASSED")
            results.append((i, True, enforced.audit_id))
        except ComplianceViolation as e:
            print_error(f"  BLOCKED: {e.result.details[:60]}...")
            results.append((i, False, None))
        print()

    # Summary
    compliant = [r for r in results if r[1]]
    print(f"Summary: {len(compliant)}/{len(outputs)} models are compliant")
    print(f"Consensus can use: Models {', '.join(str(r[0]) for r in compliant)}")

    return True


def demo_audit_trail_query():
    """
    Demo 6: Query audit trail for compliance reporting

    This demonstrates querying the immutable audit log.
    """
    print_header("DEMO 6: Audit Trail Query")

    print("Scenario: Query audit logs for compliance reporting")
    print("Expected: Retrieve all validation events from PostgreSQL\n")

    logger = AuditLogger()

    # Query recent audits
    try:
        print("Querying recent audit logs...")
        recent_audits = logger.query_audits(regulation="LGPD", limit=10)

        if not recent_audits:
            print_info("No audit logs found (database may not be set up)")
            print_info("Run: ./scripts/setup_compliance_db.sh")
            return False

        print(f"\nFound {len(recent_audits)} recent LGPD audits:\n")

        for audit in recent_audits[:5]:  # Show first 5
            status = "✅ PASSED" if audit["passed"] else "❌ FAILED"
            print(f"{status} | {audit['guardrail_name']}")
            print(f"   Timestamp: {audit['timestamp']}")
            print(f"   Details: {audit['details'][:60]}...")
            print()

        # Query violations
        print("\nQuerying violations only...")
        violations = logger.query_audits(regulation="LGPD", passed=False, limit=5)

        print(f"Found {len(violations)} violations:")
        for v in violations:
            print(f"  - {v['guardrail_name']}: {v['details'][:50]}...")

        # Get summary
        print("\nGetting compliance summary...")
        summary = logger.get_violations_summary(regulation="LGPD", days_back=7)

        print("\nLast 7 days summary:")
        print(f"  Total audits: {summary.get('total_audits', 0)}")
        print(f"  Violations: {summary.get('total_violations', 0)}")
        print(f"  Compliance rate: {summary.get('compliance_rate', 0):.1%}")

        return True

    except Exception as e:
        print_error(f"Database error: {str(e)}")
        print_info("Make sure PostgreSQL is running and schema is applied")
        print_info("Run: docker-compose up -d postgres")
        print_info("Run: ./scripts/setup_compliance_db.sh")
        return False


def demo_all():
    """Run all demos in sequence"""
    demos = [
        ("Article 18 - Non-Compliant", demo_article18_non_compliant),
        ("Article 18 - Compliant", demo_article18_compliant),
        ("Article 20 - Non-Compliant", demo_article20_non_compliant),
        ("Article 20 - Compliant", demo_article20_compliant),
        ("Batch Validation", demo_batch_validation),
        ("Audit Trail Query", demo_audit_trail_query),
    ]

    results = []
    for name, demo_func in demos:
        success = demo_func()
        results.append((name, success))

    # Final summary
    print_header("DEMO SUMMARY")

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {name}")

    passed = sum(1 for _, s in results if s)
    print(f"\n{passed}/{len(results)} demos completed successfully")

    return all(s for _, s in results)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="SENTINEL Compliance Demo - LGPD Guardrails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/demo_sentinel.py                    # Run all demos
  python scripts/demo_sentinel.py --demo article18   # Run Article 18 demos
  python scripts/demo_sentinel.py --demo article20   # Run Article 20 demos
  python scripts/demo_sentinel.py --demo audit       # Run audit trail demo
        """,
    )

    parser.add_argument(
        "--demo",
        choices=["all", "article18", "article20", "batch", "audit"],
        default="all",
        help="Which demo to run (default: all)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Print banner
    print("\n" + "=" * 70)
    print("  SENTINEL COMPLIANCE DEMO")
    print("  LGPD Guardrails - Brazil Data Protection Law")
    print("=" * 70)

    # Run selected demo
    if args.demo == "all":
        success = demo_all()
    elif args.demo == "article18":
        demo_article18_non_compliant()
        success = demo_article18_compliant()
    elif args.demo == "article20":
        demo_article20_non_compliant()
        success = demo_article20_compliant()
    elif args.demo == "batch":
        success = demo_batch_validation()
    elif args.demo == "audit":
        success = demo_audit_trail_query()

    # Exit
    print("\n" + "=" * 70)
    if success:
        print("  ✅ Demo completed successfully!")
    else:
        print("  ⚠️  Demo completed with warnings")
    print("=" * 70 + "\n")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
