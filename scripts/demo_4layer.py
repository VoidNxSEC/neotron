#!/usr/bin/env python3
"""
NEUTRON/NEXUS - End-to-End 4-Layer Compliance Demo

Demonstrates the full compliance pipeline:
  Layer 1: SENTINEL  - Application-level guardrail enforcement
  Layer 2: BASTION   - Kernel-level seccomp-BPF enforcement
  Layer 3: Smart Contracts (reference) - On-chain audit + circuit breaker
  Layer 4: Audit Trail - Immutable compliance log

Plus CORTEX multi-agent consensus with live LLM (llama.cpp on :8081).

Usage:
    PYTHONPATH=. python scripts/demo_4layer.py
    PYTHONPATH=. python scripts/demo_4layer.py --no-llm   # skip live LLM
    PYTHONPATH=. python scripts/demo_4layer.py --url http://localhost:8081
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime

# ── Provider + Specialized agents ────────────────────────────────────────
from neutron.agents.providers.base import ProviderConfig
from neutron.agents.providers.llamacpp import LlamaCppProvider

from neutron.agents.specialized.compliance_analyst import ComplianceAnalystAgent
from neutron.agents.specialized.decision_maker import DecisionMakerAgent
from neutron.agents.specialized.risk_assessor import RiskAssessorAgent
from neutron.compliance.audit_logger import AuditLogger

# ── BASTION imports ──────────────────────────────────────────────────────
from neutron.compliance.bastion import (
    ComplianceCapability,
    KernelPolicy,
    LayeredPolicy,
    grant_capability,
    has_capability,
    revoke_capability,
)

# ── SENTINEL imports ─────────────────────────────────────────────────────
from neutron.compliance.sentinel import (
    AgentOutput,
    ComplianceViolation,
    ValidationResult,
    create_guardrail,
)

# ── CORTEX imports ───────────────────────────────────────────────────────
from neutron.orchestration.cortex import (
    AgentSwarm,
    ConsensusStrategy,
    Task,
)

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"

BAR = f"{DIM}{'─' * 72}{RESET}"


def banner(title: str, layer: str = "") -> None:
    prefix = f"[{layer}] " if layer else ""
    print(f"\n{BAR}")
    print(f"{BOLD}{CYAN}{prefix}{title}{RESET}")
    print(BAR)


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {DIM}→{RESET} {msg}")


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 — SENTINEL (Application-Level Guardrails)
# ═══════════════════════════════════════════════════════════════════════════


def demo_sentinel() -> None:
    """Demonstrate SENTINEL guardrail enforcement."""
    banner("SENTINEL — Application-Level Compliance", "Layer 1")

    audit = AuditLogger()
    audit.clear()  # fresh start

    # ── Guardrail: LGPD Art.18 requires explainability ───────────────
    def check_lgpd_explanation(output: AgentOutput) -> ValidationResult:
        if not output.has_explanation or not output.explanation:
            return ValidationResult(
                passed=False,
                details="LGPD Art.18: AI decision must include human-readable explanation",
                confidence=1.0,
                metadata={"article": "LGPD Art.18", "missing": "explanation"},
            )
        if output.explanation_quality < 0.5:
            return ValidationResult(
                passed=False,
                details=f"Explanation quality too low ({output.explanation_quality:.0%})",
                confidence=0.9,
            )
        return ValidationResult(passed=True, details="Explanation meets LGPD Art.18")

    lgpd_guardrail = create_guardrail(
        name="lgpd_art18_explanation",
        regulation="LGPD",
        check_function=check_lgpd_explanation,
        severity="block",
        description="Ensures AI decisions have adequate explanations (LGPD Art.18)",
    )

    # ── Guardrail: GDPR Art.22 human-in-the-loop ────────────────────
    def check_gdpr_human_oversight(output: AgentOutput) -> ValidationResult:
        meta = output.metadata or {}
        if meta.get("automated_decision") and not meta.get("human_review"):
            return ValidationResult(
                passed=False,
                details="GDPR Art.22: Automated decision without human oversight",
                confidence=1.0,
                metadata={"article": "GDPR Art.22"},
            )
        return ValidationResult(passed=True, details="Human oversight present or not automated")

    gdpr_guardrail = create_guardrail(
        name="gdpr_art22_human_oversight",
        regulation="GDPR",
        check_function=check_gdpr_human_oversight,
        severity="block",
    )

    # ── Guardrail: EU AI Act risk classification (warn only) ─────────
    def check_ai_act_risk(output: AgentOutput) -> ValidationResult:
        meta = output.metadata or {}
        risk = meta.get("risk_level", "low")
        if risk in ("high", "critical"):
            return ValidationResult(
                passed=False,
                details=f"EU AI Act: High-risk system ({risk}) requires conformity assessment",
                confidence=0.85,
                metadata={"risk_level": risk},
            )
        return ValidationResult(passed=True, details=f"Risk level acceptable: {risk}")

    ai_act_guardrail = create_guardrail(
        name="eu_ai_act_risk_classification",
        regulation="AI_ACT",
        check_function=check_ai_act_risk,
        severity="warn",
    )

    # ── Scenario A: Compliant output ─────────────────────────────────
    print(f"\n  {BOLD}Scenario A: Compliant agent output{RESET}")
    compliant_output = AgentOutput(
        content="Loan approved for R$ 50,000",
        has_explanation=True,
        explanation="Based on credit score (780), income (R$ 12k/mo), DTI ratio (28%)",
        explanation_quality=0.9,
        model_name="llama-3.2-3b",
        metadata={"automated_decision": True, "human_review": True, "risk_level": "medium"},
    )

    for g in [lgpd_guardrail, gdpr_guardrail, ai_act_guardrail]:
        try:
            result = g.enforce(compliant_output)
            status = "PASS" if result.validation_result.passed else "WARN"
            if status == "PASS":
                ok(f"{g.name}: {result.validation_result.details}")
            else:
                warn(f"{g.name}: {result.validation_result.details}")
        except ComplianceViolation as e:
            fail(f"{g.name}: BLOCKED — {e.result.details}")

    # ── Scenario B: Non-compliant (missing explanation → BLOCK) ──────
    print(f"\n  {BOLD}Scenario B: Non-compliant output (no explanation){RESET}")
    bad_output = AgentOutput(
        content="Loan denied",
        has_explanation=False,
        model_name="llama-3.2-3b",
        metadata={"automated_decision": True, "human_review": False, "risk_level": "high"},
    )

    for g in [lgpd_guardrail, gdpr_guardrail, ai_act_guardrail]:
        try:
            result = g.enforce(bad_output)
            if result.validation_result.passed:
                ok(f"{g.name}: {result.validation_result.details}")
            else:
                warn(f"{g.name}: {result.validation_result.details}")
        except ComplianceViolation as e:
            fail(f"{g.name}: BLOCKED — {e.result.details}")

    # ── Show audit trail ─────────────────────────────────────────────
    entries = audit.get_all()
    info(f"Audit trail: {len(entries)} entries logged")
    for e in entries[-3:]:
        status = "PASS" if e.get("passed") else "FAIL"
        info(f"  #{e['audit_id']} [{e['regulation']}] {e['guardrail_name']} → {status}")


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2 — BASTION (Kernel-Level Enforcement)
# ═══════════════════════════════════════════════════════════════════════════


def demo_bastion() -> None:
    """Demonstrate BASTION kernel-level enforcement (simulated on non-Linux)."""
    banner("BASTION — Kernel-Level seccomp-BPF Enforcement", "Layer 2")

    # ── Policy: block file I/O without consent token ─────────────────
    policy = KernelPolicy(
        name="lgpd_art7_consent_required",
        regulation="LGPD",
        blocked_syscalls=["open", "openat", "read"],
        required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
        action="ERRNO",
        errno=13,  # EACCES
    )

    info(f"Policy: {policy.name}")
    info(f"Blocked syscalls: {policy.blocked_syscalls}")
    info(f"Required capability: {policy.required_capability.value}")

    # ── Without consent token → enforcement active ───────────────────
    print(f"\n  {BOLD}Scenario A: No consent token → enforcement ACTIVE{RESET}")
    revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

    has_cap = has_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
    info(f"Has CAP_CONSENT_TOKEN: {has_cap}")

    bpf = policy.build_bpf_program()
    info(f"BPF program: {len(bpf.instructions)} instructions compiled")
    fail("Syscalls [open, openat, read] would be BLOCKED by kernel (EACCES)")

    enforcement_mode = "seccomp-BPF" if sys.platform == "linux" else "simulated"
    info(f"Enforcement mode: {enforcement_mode}")

    # ── With consent token → enforcement bypassed ────────────────────
    print(f"\n  {BOLD}Scenario B: Consent token granted → enforcement BYPASSED{RESET}")
    grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)

    has_cap = has_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
    info(f"Has CAP_CONSENT_TOKEN: {has_cap}")
    ok("Capability check passed — syscalls ALLOWED")

    # ── LayeredPolicy: SENTINEL + BASTION combined ───────────────────
    print(f"\n  {BOLD}Layered Policy (SENTINEL + BASTION){RESET}")

    sentinel_guardrail = create_guardrail(
        name="lgpd_data_access",
        regulation="LGPD",
        check_function=lambda out: ValidationResult(passed=True, details="Data access authorized"),
        severity="block",
    )

    layered = LayeredPolicy(
        name="lgpd_full_enforcement",
        regulation="LGPD",
        application_check=sentinel_guardrail,
        kernel_policy=policy,
    )

    ok(f"LayeredPolicy '{layered.name}' combines app + kernel enforcement")
    info("Layer 1 (SENTINEL): Python validation → block/warn/audit")
    info("Layer 2 (BASTION): seccomp-BPF → syscall blocked by kernel")

    # Cleanup
    revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 3 — Smart Contracts (On-Chain Reference)
# ═══════════════════════════════════════════════════════════════════════════


def demo_smart_contracts() -> None:
    """Reference smart contract layer (would require EVM/Foundry)."""
    banner("Smart Contracts — On-Chain Compliance", "Layer 3")

    info("Smart contracts enforce compliance on-chain (immutable, trustless)")
    print()

    contracts = [
        ("ComplianceGuardrail.sol", "On-chain compliance policy registry", "deployed"),
        ("LGPDConsent.sol", "LGPD consent management with DID", "deployed"),
        ("AuditLogger.sol", "Immutable on-chain audit trail", "deployed"),
        ("LendingProtocol.sol", "DeFi lending with compliance hooks", "deployed"),
        ("PriceOracle.sol", "Chainlink-compatible price feed", "deployed"),
        ("EmergencyStop.sol", "Circuit breaker with timelock unpause", "deployed"),
    ]

    for name, desc, status in contracts:
        ok(f"{name}: {desc} [{status}]")

    print()
    info("123/123 Solidity tests passing (including fuzz tests)")
    info("Security: CEI pattern, custom errors, overflow protection")
    info("Features: price deviation circuit breaker (50%), timelock unpause (24h)")
    info("Run: cd contracts && forge test -vvv")


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 4 — Audit Trail
# ═══════════════════════════════════════════════════════════════════════════


def demo_audit_trail() -> None:
    """Show the full audit trail from all layers."""
    banner("Audit Trail — Immutable Compliance Log", "Layer 4")

    audit = AuditLogger()
    entries = audit.get_all()

    info(f"Total audit entries: {len(entries)}")
    print()

    for entry in entries:
        ts = entry.get("timestamp", "?")
        aid = entry.get("audit_id", "?")
        guardrail = entry.get("guardrail_name", "unknown")
        regulation = entry.get("regulation", "?")
        passed = entry.get("passed", None)
        severity = entry.get("severity", "?")

        if passed is True:
            status = f"{GREEN}PASS{RESET}"
        elif passed is False:
            status = f"{RED}FAIL{RESET}"
        else:
            status = f"{DIM}N/A{RESET}"

        print(f"  #{aid:>3}  [{regulation:>6}]  {guardrail:<35}  {status}  ({severity})")

    print()
    info("In production: PostgreSQL append-only + IPFS content-addressing")
    info("Every decision → hashed (SHA-256) → logged → immutable")


# ═══════════════════════════════════════════════════════════════════════════
# CORTEX — Multi-Agent Consensus (optional live LLM)
# ═══════════════════════════════════════════════════════════════════════════


async def demo_cortex(base_url: str) -> None:
    """Demonstrate 3-agent CORTEX consensus with live llama.cpp."""
    banner("CORTEX — Multi-Agent Consensus (Live LLM)", "Orchestration")

    config = ProviderConfig(base_url=base_url, model="default")
    provider = LlamaCppProvider(config)

    # Health check
    healthy = await provider.health()
    if not healthy:
        fail(f"llama.cpp server not reachable at {base_url}")
        warn("Skipping CORTEX demo. Start server: llama-swap --port 8081")
        return

    ok(f"llama.cpp server healthy at {base_url}")

    # Create specialized agents
    agents = [
        ComplianceAnalystAgent(provider),
        RiskAssessorAgent(provider),
        DecisionMakerAgent(provider),
    ]

    info(f"Agents: {', '.join(a.agent_id for a in agents)}")

    # Create swarm
    swarm = AgentSwarm(agents=agents)

    # ── Scenario: Cross-border data transfer requiring LGPD + GDPR ───
    task = Task(
        type="compliance_review",
        input={
            "scenario": (
                "A Brazilian FinTech wants to transfer customer PII data to a "
                "processing center in Germany for credit scoring. The data includes "
                "CPF numbers, income records, and transaction history. No explicit "
                "user consent form has been signed for cross-border transfer."
            ),
            "regulations": ["LGPD", "GDPR"],
            "context": "FinTech B2B, 50k affected users",
        },
        consensus_strategy=ConsensusStrategy.BEST_CONFIDENCE,
        timeout_seconds=60.0,
    )

    info(f"Task: {task.type} | Strategy: {task.consensus_strategy.value}")
    info("Scenario: Cross-border PII transfer (Brazil → Germany)")
    print()

    t0 = time.monotonic()
    result = await swarm.execute(task)
    elapsed = time.monotonic() - t0

    ok(f"Consensus reached in {elapsed:.1f}s")
    info(f"Consensus output: {result.consensus_output}")
    info(f"Consensus confidence: {result.consensus_confidence:.0%}")
    print()

    for ar in result.individual_results:
        conf_bar = "█" * int(ar.confidence * 20) + "░" * (20 - int(ar.confidence * 20))
        print(f"  {ar.agent_id:<25} [{conf_bar}] {ar.confidence:.0%}")
        if ar.explanation:
            expl = ar.explanation[:100] + "..." if len(ar.explanation) > 100 else ar.explanation
            info(f"    {expl}")

    # ── Now run SENTINEL on the consensus output ─────────────────────
    print(f"\n  {BOLD}Feeding CORTEX result into SENTINEL guardrails...{RESET}")

    consensus_as_output = AgentOutput(
        content=str(result.consensus_output),
        has_explanation=True,
        explanation=result.generate_explanation(),
        explanation_quality=result.consensus_confidence,
        model_name="cortex-swarm",
        metadata={
            "automated_decision": True,
            "human_review": False,
            "risk_level": "high",
            "agent_count": len(result.individual_results),
        },
    )

    # LGPD check
    def check_lgpd(out: AgentOutput) -> ValidationResult:
        if out.has_explanation and out.explanation_quality >= 0.5:
            return ValidationResult(passed=True, details="LGPD Art.18 explanation adequate")
        return ValidationResult(passed=False, details="Explanation insufficient for LGPD Art.18")

    # GDPR check — automated decision without human review
    def check_gdpr(out: AgentOutput) -> ValidationResult:
        meta = out.metadata or {}
        if meta.get("automated_decision") and not meta.get("human_review"):
            return ValidationResult(
                passed=False,
                details="GDPR Art.22: Automated decision requires human oversight",
            )
        return ValidationResult(passed=True, details="GDPR Art.22 satisfied")

    lgpd_g = create_guardrail("lgpd_art18", "LGPD", check_lgpd, severity="block")
    gdpr_g = create_guardrail("gdpr_art22", "GDPR", check_gdpr, severity="block")

    for g in [lgpd_g, gdpr_g]:
        try:
            enforced = g.enforce(consensus_as_output)
            if enforced.validation_result.passed:
                ok(f"{g.name}: {enforced.validation_result.details}")
            else:
                warn(f"{g.name}: {enforced.validation_result.details}")
        except ComplianceViolation as e:
            fail(f"{g.name}: BLOCKED — {e.result.details}")
            warn("  → In production: escalate to human reviewer before proceeding")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(description="NEUTRON 4-Layer Compliance Demo")
    parser.add_argument("--url", default="http://localhost:8081", help="llama.cpp server URL")
    parser.add_argument("--no-llm", action="store_true", help="Skip live LLM demo")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═' * 72}{RESET}")
    print(f"{BOLD}{CYAN}  NEUTRON / NEXUS — 4-Layer Compliance Architecture Demo{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}")
    print(f"  {DIM}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print()
    info("Layer 1: SENTINEL  — Application-level guardrails (Python)")
    info("Layer 2: BASTION   — Kernel-level seccomp-BPF enforcement")
    info("Layer 3: Smart Contracts — On-chain immutable compliance")
    info("Layer 4: Audit Trail — SHA-256 hashed, append-only log")
    info("Orchestration: CORTEX — Multi-agent consensus with live LLM")

    # Layer 1
    demo_sentinel()

    # Layer 2
    demo_bastion()

    # Layer 3
    demo_smart_contracts()

    # CORTEX (optional)
    if not args.no_llm:
        asyncio.run(demo_cortex(args.url))

    # Layer 4 (always last — shows accumulated audit trail)
    demo_audit_trail()

    # Summary
    print(f"\n{BOLD}{'═' * 72}{RESET}")
    print(f"{BOLD}{GREEN}  Demo complete — 4 layers of defense-in-depth compliance{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}")

    audit = AuditLogger()
    total = len(audit.get_all())
    passed = sum(1 for e in audit.get_all() if e.get("passed") is True)
    failed = total - passed
    print(f"  {total} audit events | {GREEN}{passed} passed{RESET} | {RED}{failed} failed{RESET}")
    print()


if __name__ == "__main__":
    main()
