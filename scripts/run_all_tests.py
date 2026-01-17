#!/usr/bin/env python3
"""
Comprehensive Test Runner for NEXUS Platform

Runs all tests across all phases and generates stakeholder-friendly reports.

Usage:
    python scripts/run_all_tests.py              # Run all tests
    python scripts/run_all_tests.py --coverage   # Run with coverage report
    python scripts/run_all_tests.py --fast       # Skip slow integration tests
    python scripts/run_all_tests.py --report     # Generate stakeholder report
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class TestSuite:
    """Test suite configuration"""
    def __init__(self, name: str, path: str, description: str, phase: str):
        self.name = name
        self.path = path
        self.description = description
        self.phase = phase
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.duration = 0.0
        self.success = False


# Define all test suites organized by phase
TEST_SUITES = [
    # Phase 1: SENTINEL - Compliance Guardrails
    TestSuite(
        name="SENTINEL Core",
        path="tests/compliance/test_sentinel.py",
        description="Core compliance guardrail framework",
        phase="Phase 1"
    ),
    TestSuite(
        name="LGPD Compliance",
        path="tests/compliance/auditors/test_lgpd.py",
        description="Brazilian data protection law (LGPD) compliance",
        phase="Phase 1"
    ),
    TestSuite(
        name="Temporal Integration",
        path="tests/workflows/test_sentinel_temporal.py",
        description="SENTINEL integration with Temporal workflows",
        phase="Phase 1"
    ),

    # Phase 2: CORTEX + SYNAPSE + GDPR
    TestSuite(
        name="CORTEX Multi-Agent",
        path="tests/orchestration/test_cortex.py",
        description="Multi-agent orchestration and consensus",
        phase="Phase 2"
    ),
    TestSuite(
        name="SYNAPSE Memory",
        path="tests/memory/test_memory_store.py",
        description="Long-term memory with semantic search",
        phase="Phase 2"
    ),
    TestSuite(
        name="GDPR Compliance",
        path="tests/compliance/auditors/test_gdpr.py",
        description="EU data protection law (GDPR) compliance",
        phase="Phase 2"
    ),
    TestSuite(
        name="NEXUS Integration",
        path="tests/orchestration/test_nexus_workflow.py",
        description="Complete NEXUS workflow integration",
        phase="Phase 2"
    ),

    # Phase 3: ORACLE + EU AI Act
    TestSuite(
        name="ORACLE Explainability",
        path="tests/reasoning/test_oracle.py",
        description="AI explainability framework (5 strategies)",
        phase="Phase 3"
    ),
    TestSuite(
        name="EU AI Act Compliance",
        path="tests/compliance/auditors/test_ai_act.py",
        description="EU AI Act compliance (Articles 5, 13, 14)",
        phase="Phase 3"
    ),
]


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


def run_test_suite(suite: TestSuite, coverage: bool = False, fast: bool = False) -> bool:
    """Run a single test suite and capture results"""
    print_subheader(f"{suite.phase}: {suite.name}")
    print_info(suite.description)

    # Check if test file exists
    test_path = Path(suite.path)
    if not test_path.exists():
        print_warning(f"Test file not found: {suite.path}")
        suite.skipped = 1
        return False

    # Build pytest command
    cmd = ["pytest", suite.path, "-v"]

    if fast:
        cmd.extend(["-m", "not slow"])

    if coverage:
        cmd.extend([
            "--cov=neutron",
            "--cov-report=term-missing",
            "--cov-append"
        ])

    # Run tests
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per suite
        )
        suite.duration = time.time() - start_time

        # Parse results from output
        output = result.stdout + result.stderr

        # Extract test counts
        if "passed" in output:
            for line in output.split('\n'):
                if 'passed' in line or 'failed' in line:
                    # Parse pytest summary line
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'passed' in part and i > 0:
                            suite.passed = int(parts[i-1])
                        if 'failed' in part and i > 0:
                            suite.failed = int(parts[i-1])
                        if 'skipped' in part and i > 0:
                            suite.skipped = int(parts[i-1])

        suite.success = result.returncode == 0

        # Print results
        if suite.success:
            print_success(
                f"Passed: {suite.passed} tests in {suite.duration:.2f}s"
            )
        else:
            print_error(
                f"Failed: {suite.failed} failed, {suite.passed} passed in {suite.duration:.2f}s"
            )
            # Print failure details
            if suite.failed > 0:
                print(f"\n{Colors.RED}Failure details:{Colors.END}")
                print(output[-2000:])  # Last 2000 chars

        return suite.success

    except subprocess.TimeoutExpired:
        suite.duration = time.time() - start_time
        print_error(f"Test suite timed out after {suite.duration:.2f}s")
        suite.failed = 1
        return False
    except Exception as e:
        suite.duration = time.time() - start_time
        print_error(f"Error running tests: {e}")
        suite.failed = 1
        return False


def generate_summary(suites: List[TestSuite]) -> Dict:
    """Generate test execution summary"""
    total_passed = sum(s.passed for s in suites)
    total_failed = sum(s.failed for s in suites)
    total_skipped = sum(s.skipped for s in suites)
    total_duration = sum(s.duration for s in suites)
    total_suites = len(suites)
    successful_suites = sum(1 for s in suites if s.success)

    return {
        "total_tests": total_passed + total_failed,
        "passed": total_passed,
        "failed": total_failed,
        "skipped": total_skipped,
        "total_suites": total_suites,
        "successful_suites": successful_suites,
        "failed_suites": total_suites - successful_suites,
        "duration": total_duration,
        "success_rate": (total_passed / (total_passed + total_failed) * 100) if (total_passed + total_failed) > 0 else 0,
        "suite_success_rate": (successful_suites / total_suites * 100) if total_suites > 0 else 0,
    }


def print_summary(suites: List[TestSuite]):
    """Print test execution summary"""
    print_header("Test Execution Summary")

    summary = generate_summary(suites)

    # Overall results
    print(f"{Colors.BOLD}Overall Results:{Colors.END}")
    print(f"  Total Tests:     {summary['total_tests']}")
    print(f"  {Colors.GREEN}✓ Passed:{Colors.END}        {summary['passed']}")
    print(f"  {Colors.RED}✗ Failed:{Colors.END}        {summary['failed']}")
    print(f"  {Colors.YELLOW}⊘ Skipped:{Colors.END}       {summary['skipped']}")
    print(f"  Success Rate:    {summary['success_rate']:.1f}%")
    print(f"  Total Duration:  {summary['duration']:.2f}s")

    print(f"\n{Colors.BOLD}Test Suites:{Colors.END}")
    print(f"  Total Suites:    {summary['total_suites']}")
    print(f"  {Colors.GREEN}✓ Successful:{Colors.END}    {summary['successful_suites']}")
    print(f"  {Colors.RED}✗ Failed:{Colors.END}        {summary['failed_suites']}")
    print(f"  Suite Success:   {summary['suite_success_rate']:.1f}%")

    # Phase breakdown
    print(f"\n{Colors.BOLD}Phase Breakdown:{Colors.END}")
    for phase in ["Phase 1", "Phase 2", "Phase 3"]:
        phase_suites = [s for s in suites if s.phase == phase]
        if phase_suites:
            phase_passed = sum(s.passed for s in phase_suites)
            phase_failed = sum(s.failed for s in phase_suites)
            phase_success = sum(1 for s in phase_suites if s.success)
            phase_total = len(phase_suites)

            status = Colors.GREEN if phase_success == phase_total else Colors.YELLOW
            print(f"  {status}{phase}:{Colors.END} {phase_success}/{phase_total} suites, {phase_passed} passed, {phase_failed} failed")

    # Failed suites detail
    failed_suites = [s for s in suites if not s.success and not s.skipped]
    if failed_suites:
        print(f"\n{Colors.RED}{Colors.BOLD}Failed Suites:{Colors.END}")
        for suite in failed_suites:
            print(f"  {Colors.RED}✗{Colors.END} {suite.name} ({suite.phase})")


def generate_stakeholder_report(suites: List[TestSuite], output_file: str):
    """Generate stakeholder-friendly HTML report"""
    summary = generate_summary(suites)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>NEXUS Platform - Test Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .metric.success .metric-value {{ color: #22c55e; }}
        .metric.warning .metric-value {{ color: #f59e0b; }}
        .metric.error .metric-value {{ color: #ef4444; }}
        .phase-section {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .phase-header {{
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }}
        .test-suite {{
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #e5e7eb;
            background: #f9fafb;
        }}
        .test-suite.success {{ border-left-color: #22c55e; }}
        .test-suite.failed {{ border-left-color: #ef4444; }}
        .test-suite.skipped {{ border-left-color: #f59e0b; }}
        .test-suite-name {{
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 5px;
        }}
        .test-suite-description {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        .test-suite-stats {{
            display: flex;
            gap: 15px;
            font-size: 0.9em;
        }}
        .stat {{ display: flex; align-items: center; gap: 5px; }}
        .stat.passed {{ color: #22c55e; }}
        .stat.failed {{ color: #ef4444; }}
        .stat.duration {{ color: #6b7280; }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
        }}
        .badge.success {{ background: #dcfce7; color: #166534; }}
        .badge.warning {{ background: #fef3c7; color: #92400e; }}
        .badge.error {{ background: #fee2e2; color: #991b1b; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NEXUS Platform Test Report</h1>
        <p>Comprehensive validation of all platform components</p>
        <p style="font-size: 0.9em; margin-top: 15px;">Generated: {timestamp}</p>
    </div>

    <div class="summary">
        <div class="metric success">
            <div class="metric-label">Tests Passed</div>
            <div class="metric-value">{summary['passed']}/{summary['total_tests']}</div>
        </div>
        <div class="metric {'success' if summary['failed'] == 0 else 'error'}">
            <div class="metric-label">Tests Failed</div>
            <div class="metric-value">{summary['failed']}</div>
        </div>
        <div class="metric success">
            <div class="metric-label">Success Rate</div>
            <div class="metric-value">{summary['success_rate']:.1f}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">Total Duration</div>
            <div class="metric-value">{summary['duration']:.1f}s</div>
        </div>
    </div>
"""

    # Group suites by phase
    phases = {}
    for suite in suites:
        if suite.phase not in phases:
            phases[suite.phase] = []
        phases[suite.phase].append(suite)

    # Generate phase sections
    for phase_name in ["Phase 1", "Phase 2", "Phase 3"]:
        if phase_name in phases:
            phase_suites = phases[phase_name]
            phase_success = sum(1 for s in phase_suites if s.success)
            phase_total = len(phase_suites)

            badge_class = "success" if phase_success == phase_total else "warning" if phase_success > 0 else "error"

            html += f"""
    <div class="phase-section">
        <div class="phase-header">
            {phase_name}
            <span class="badge {badge_class}">{phase_success}/{phase_total} suites passed</span>
        </div>
"""

            for suite in phase_suites:
                status_class = "success" if suite.success else "skipped" if suite.skipped else "failed"

                html += f"""
        <div class="test-suite {status_class}">
            <div class="test-suite-name">{suite.name}</div>
            <div class="test-suite-description">{suite.description}</div>
            <div class="test-suite-stats">
"""
                if not suite.skipped:
                    html += f"""
                <div class="stat passed">✓ {suite.passed} passed</div>
"""
                    if suite.failed > 0:
                        html += f"""
                <div class="stat failed">✗ {suite.failed} failed</div>
"""
                    html += f"""
                <div class="stat duration">⏱ {suite.duration:.2f}s</div>
"""
                else:
                    html += f"""
                <div class="stat">⊘ Skipped</div>
"""

                html += """
            </div>
        </div>
"""

            html += """
    </div>
"""

    html += f"""
    <div class="footer">
        <p><strong>NEXUS Platform</strong> - Enterprise-Grade AI Agent Orchestration</p>
        <p>Production-Ready • Compliant • Explainable</p>
    </div>
</body>
</html>
"""

    # Write report
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    print_success(f"Stakeholder report generated: {output_file}")


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description="NEXUS Platform Test Runner")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--report", action="store_true", help="Generate stakeholder HTML report")
    parser.add_argument("--phase", choices=["1", "2", "3"], help="Run only specific phase")
    args = parser.parse_args()

    print_header("NEXUS Platform - Comprehensive Test Suite")
    print_info(f"Running tests for all phases...")
    print_info(f"Coverage: {'Enabled' if args.coverage else 'Disabled'}")
    print_info(f"Mode: {'Fast (no slow tests)' if args.fast else 'Complete'}")

    # Filter suites by phase if specified
    suites_to_run = TEST_SUITES
    if args.phase:
        phase_name = f"Phase {args.phase}"
        suites_to_run = [s for s in TEST_SUITES if s.phase == phase_name]
        print_info(f"Running only {phase_name} tests")

    # Run all test suites
    start_time = time.time()
    all_passed = True

    for suite in suites_to_run:
        success = run_test_suite(suite, coverage=args.coverage, fast=args.fast)
        if not success:
            all_passed = False

    total_duration = time.time() - start_time

    # Print summary
    print_summary(suites_to_run)

    # Generate stakeholder report if requested
    if args.report:
        print_subheader("Generating Stakeholder Report")
        report_file = "reports/test_report.html"
        generate_stakeholder_report(suites_to_run, report_file)
        print_info(f"Open {report_file} in a browser to view the report")

    # Final status
    print_header("Test Run Complete")
    if all_passed:
        print_success(f"All test suites passed! ✓ Total time: {total_duration:.2f}s")
        return 0
    else:
        print_error(f"Some test suites failed. Total time: {total_duration:.2f}s")
        return 1


if __name__ == "__main__":
    sys.exit(main())
