#!/usr/bin/env python3
"""
CORTEX Live Demo - Multi-Agent Consensus with LLM

Demonstrates 3 specialized agents (ComplianceAnalyst, RiskAssessor, DecisionMaker)
coordinated by CORTEX's AgentSwarm against a live llama.cpp server.

Usage:
    PYTHONPATH=. python scripts/demo_cortex_live.py
    # Or with custom server:
    LLAMACPP_URL=http://localhost:8081 PYTHONPATH=. python scripts/demo_cortex_live.py
"""

import asyncio
import os
import sys
import time

from neutron.agents.providers import LlamaCppProvider
from neutron.agents.specialized import (
    ComplianceAnalystAgent,
    DecisionMakerAgent,
    RiskAssessorAgent,
)
from neutron.orchestration.cortex import AgentSwarm, ConsensusStrategy, Task


SCENARIOS = [
    {
        "name": "Loan Approval - Low Risk",
        "task_type": "loan_approval",
        "input": {
            "customer_id": "BR-12345",
            "loan_amount": 50000,
            "currency": "BRL",
            "purpose": "home renovation",
            "credit_score": 720,
            "income": 8000,
            "existing_debt": 15000,
            "country": "Brazil",
        },
        "strategy": ConsensusStrategy.BEST_CONFIDENCE,
    },
    {
        "name": "High-Risk Transaction - AML Check",
        "task_type": "transaction_review",
        "input": {
            "transaction_id": "TX-98765",
            "amount": 500000,
            "currency": "USD",
            "sender_country": "Cayman Islands",
            "receiver_country": "Switzerland",
            "purpose": "investment transfer",
            "sender_pep_status": True,
            "frequency": "first_transaction",
        },
        "strategy": ConsensusStrategy.MAJORITY_VOTE,
    },
    {
        "name": "AI Model Deployment - EU AI Act",
        "task_type": "model_deployment",
        "input": {
            "model_name": "credit-scoring-v3",
            "model_type": "gradient_boosted_trees",
            "use_case": "automated credit decisions",
            "affected_persons": 50000,
            "data_sources": ["credit_bureau", "bank_transactions", "social_media"],
            "explainability": "SHAP values available",
            "human_oversight": "appeal process exists",
            "jurisdiction": "EU",
        },
        "strategy": ConsensusStrategy.MAJORITY_VOTE,
    },
]


def print_header(text: str, char: str = "=") -> None:
    width = 70
    print()
    print(char * width)
    print(f"  {text}")
    print(char * width)


def print_agent_result(r) -> None:
    output_str = str(r.output)
    if len(output_str) > 80:
        output_str = output_str[:80] + "..."
    print(f"  [{r.agent_id:20s}] output={output_str!r}")
    print(f"  {'':20s}  confidence={r.confidence:.2f}  time={r.processing_time_ms:.0f}ms")
    expl = str(r.explanation) if r.explanation else ""
    if len(expl) > 120:
        expl = expl[:120] + "..."
    if expl:
        print(f"  {'':20s}  reasoning: {expl}")


async def run_scenario(swarm: AgentSwarm, scenario: dict) -> None:
    print_header(f"SCENARIO: {scenario['name']}", "-")
    print(f"  Strategy: {scenario['strategy'].value}")
    print(f"  Task type: {scenario['task_type']}")
    print()

    task = Task(
        type=scenario["task_type"],
        input=scenario["input"],
        consensus_strategy=scenario["strategy"],
        timeout_seconds=120,
    )

    start = time.monotonic()
    result = await swarm.execute(task, generate_explanation=True)
    total_ms = (time.monotonic() - start) * 1000

    print("  --- Individual Agents ---")
    for r in result.individual_results:
        print_agent_result(r)
        print()

    print("  --- Consensus ---")
    print(f"  Output:     {result.consensus_output!r}")
    print(f"  Confidence: {result.consensus_confidence:.2f}")
    print(f"  Agreement:  {result.agreement_score:.2f}")
    print(f"  Strategy:   {result.consensus_strategy.value}")
    print(f"  Total time: {total_ms:.0f}ms")

    if result.explanation:
        print()
        print("  --- ORACLE Explanation ---")
        readable = result.explanation.to_human_readable()
        for line in readable.split("\n"):
            print(f"  {line}")


async def main() -> None:
    url = os.getenv("LLAMACPP_URL", "http://localhost:8081")

    print_header("CORTEX Multi-Agent Live Demo")
    print(f"  Server: {url}")
    print()

    # Create provider and check health
    provider = LlamaCppProvider(base_url=url)
    healthy = await provider.health()
    print(f"  Provider: {provider}")
    print(f"  Health:   {'OK' if healthy else 'FAILED'}")

    if not healthy:
        print("\n  ERROR: llama.cpp server not reachable. Start it first.")
        print(f"  Expected at: {url}")
        sys.exit(1)

    # Create agents
    analyst = ComplianceAnalystAgent(provider)
    risk = RiskAssessorAgent(provider)
    decision = DecisionMakerAgent(provider)

    print(f"\n  Agents: {analyst.agent_id}, {risk.agent_id}, {decision.agent_id}")

    # Create swarm
    swarm = AgentSwarm([analyst, risk, decision], name="compliance_swarm")
    print(f"  Swarm:  {swarm.name} ({swarm.num_agents} agents)")

    # Run scenarios
    for scenario in SCENARIOS:
        await run_scenario(swarm, scenario)

    print_header("DEMO COMPLETE")
    print(f"  Ran {len(SCENARIOS)} scenarios with {swarm.num_agents} agents each")
    print()


if __name__ == "__main__":
    asyncio.run(main())
