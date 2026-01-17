#!/usr/bin/env python3
"""
NEXUS Phase 2 Demo - Multi-Agent Orchestration with Memory & Compliance

Interactive demonstration of Phase 2 integration:
- CORTEX: Multi-agent consensus
- SYNAPSE: Long-term memory with semantic search
- GDPR: Compliance guardrails

Usage:
    python scripts/demo_nexus.py

Demos:
    1. Multi-Agent Consensus (CORTEX only)
    2. Memory-Enabled Agent (SYNAPSE integration)
    3. GDPR Compliant Low-Risk Decision
    4. GDPR Compliant High-Risk Decision (with human review)
    5. GDPR Violation - High-Risk without Review (BLOCKED)
    6. Customer Data Erasure (GDPR Article 17)
    7. Full NEXUS Workflow - Complete Integration

Requirements:
    - PostgreSQL with pgvector (for SYNAPSE demos)
    - neutron package installed
"""

import asyncio
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

# CORTEX - Multi-Agent
from neutron.orchestration.cortex import (
    Task,
    AgentResult,
    ConsensusEngine,
)

# SYNAPSE - Memory
from neutron.memory import MemoryStore

# GDPR - Compliance
from neutron.compliance.sentinel import ComplianceViolation
from neutron.compliance.auditors import validate_with_gdpr

# NEXUS - Integrated Workflow
from neutron.orchestration.nexus_workflow import (
    NexusAgent,
    NexusSwarm,
    create_nexus_swarm,
    execute_nexus_workflow,
)


# =============================================================================
# Demo Utilities
# =============================================================================

def print_header(title: str):
    """Print demo section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_section(title: str):
    """Print subsection"""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}\n")


def create_mock_embedding(seed: int = 42) -> np.ndarray:
    """Create mock 1536-dimensional embedding"""
    np.random.seed(seed)
    return np.random.rand(1536)


async def mock_agent_execute(task: Task, context: str = "") -> str:
    """Mock agent execution (replace with real LLM in production)"""
    return f"Analysis: {task.description} | Context: {context[:50]}..."


# =============================================================================
# Demo 1: Multi-Agent Consensus (CORTEX Only)
# =============================================================================

def demo_1_cortex_consensus():
    """
    Demo 1: Multi-Agent Consensus

    Shows CORTEX consensus algorithms without memory or compliance.
    """
    print_header("DEMO 1: Multi-Agent Consensus (CORTEX)")

    print("Creating 3 agents for classification task...")
    agents_results = [
        AgentResult(agent_id="agent_1", output="spam", confidence=0.9),
        AgentResult(agent_id="agent_2", output="spam", confidence=0.85),
        AgentResult(agent_id="agent_3", output="ham", confidence=0.7),
    ]

    print(f"\nIndividual agent outputs:")
    for result in agents_results:
        print(f"  - {result.agent_id}: {result.output} (confidence: {result.confidence})")

    print("\n🔄 Applying majority_vote consensus...")
    consensus_output, consensus_confidence, agreement_score = (
        ConsensusEngine.majority_vote(agents_results)
    )

    print(f"\n✅ Consensus Result:")
    print(f"  Output: {consensus_output}")
    print(f"  Confidence: {consensus_confidence:.2f}")
    print(f"  Agreement: {agreement_score:.2f} (2/3 agents agreed)")


# =============================================================================
# Demo 2: Memory-Enabled Agent (SYNAPSE Integration)
# =============================================================================

async def demo_2_memory_enabled_agent():
    """
    Demo 2: Memory-Enabled Agent

    Shows agent using SYNAPSE for context-aware decision making.
    """
    print_header("DEMO 2: Memory-Enabled Agent (SYNAPSE)")

    print("Creating memory store (requires PostgreSQL + pgvector)...")
    try:
        memory_store = MemoryStore()
        print("✅ Connected to memory store\n")
    except Exception as e:
        print(f"⚠️  Memory store unavailable: {e}")
        print("   (Skipping demo - requires PostgreSQL with pgvector)\n")
        return

    print("Creating agent with memory capabilities...")
    agent = NexusAgent(
        agent_id="financial_advisor",
        name="Financial Advisor AI",
        memory_store=memory_store,
        enable_gdpr=False  # Disabled for this demo
    )

    print("\n📝 Storing past customer interactions as memories...")
    memories = [
        "Customer prefers low-risk investments",
        "Customer is saving for retirement in 20 years",
        "Customer has moderate risk tolerance",
    ]

    for i, memory_content in enumerate(memories):
        memory_id = memory_store.store(
            agent_id=agent.agent_id,
            content=memory_content,
            embedding=create_mock_embedding(seed=100 + i),
            metadata={"customer_id": "customer_123"},
            importance_score=0.8
        )
        print(f"  ✓ Stored memory {memory_id}: {memory_content}")

    print("\n🔍 Agent retrieving memories for new task...")
    task = Task(
        task_id="task_advice",
        description="Provide investment advice",
        input_data={
            "query_embedding": create_mock_embedding(seed=100),  # Similar to stored
            "output_embedding": create_mock_embedding(seed=200),
        },
        consensus_strategy="majority_vote"
    )

    result = await agent.execute_with_memory(
        task=task,
        customer_id="customer_123",
        retrieve_k=3,
        store_result=True
    )

    print(f"\n✅ Agent Result (with memory context):")
    print(f"  Output: {result.output}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Memories used: {result.metadata['memory_count']}")

    print("\n🧹 Cleaning up demo memories...")
    deleted = memory_store.delete_by_customer("customer_123")
    print(f"  ✓ Deleted {deleted} memories")


# =============================================================================
# Demo 3: GDPR Compliant Low-Risk Decision
# =============================================================================

def demo_3_gdpr_low_risk():
    """
    Demo 3: GDPR Compliant Low-Risk Decision

    Shows low-risk decision that passes GDPR without human review.
    """
    print_header("DEMO 3: GDPR Compliant Low-Risk Decision")

    print("Creating low-risk decision output...")
    from neutron.compliance.sentinel import AgentOutput

    output = AgentOutput(
        content="Recommendation: Consider diversifying your portfolio with index funds",
        metadata={
            "risk_level": "low",  # Low risk doesn't require human review
            "data_access_enabled": True,
            "data_categories": ["investment_preferences"],
            "retention_period": "90 days",
            "export_format": "JSON",
            "processes_personal_data": True,
            "erasure_supported": True,
            "erasure_endpoint": "/api/v1/customers/{id}/delete"
        }
    )

    print("\n🔍 Validating with GDPR guardrails...")
    results = validate_with_gdpr(output)

    print(f"\n✅ GDPR Validation Results:")
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        article = result.metadata.get("article", "Unknown")
        print(f"  {status} - {article}")
        print(f"       {result.details}")

    all_passed = all(r.passed for r in results)
    if all_passed:
        print("\n🎉 All GDPR guardrails passed! Output can be delivered.")
    else:
        print("\n⚠️  Some GDPR warnings (won't block low-risk decisions)")


# =============================================================================
# Demo 4: GDPR Compliant High-Risk Decision (with Human Review)
# =============================================================================

def demo_4_gdpr_high_risk_compliant():
    """
    Demo 4: GDPR High-Risk Decision with Human Review

    Shows high-risk decision with proper human oversight (GDPR Art. 22).
    """
    print_header("DEMO 4: GDPR High-Risk Decision (with Human Review)")

    print("Creating high-risk decision with human review...")
    from neutron.compliance.sentinel import AgentOutput

    timestamp = datetime.utcnow().isoformat()
    output = AgentOutput(
        content="Loan application APPROVED - $50,000 at 4.5% APR",
        metadata={
            "risk_level": "high",  # High risk REQUIRES human review
            "human_reviewed": True,
            "reviewer_id": "compliance_officer_001",
            "review_timestamp": timestamp,
            "data_access_enabled": True,
            "data_categories": ["financial_data", "credit_score", "employment"],
            "retention_period": "7 years",
            "export_format": "PDF",
            "processes_personal_data": True,
            "erasure_supported": True,
            "erasure_endpoint": "/api/v1/loans/{id}/delete"
        }
    )

    print(f"\n📋 Decision metadata:")
    print(f"  Risk Level: high")
    print(f"  Human Reviewed: ✅ Yes")
    print(f"  Reviewer: compliance_officer_001")
    print(f"  Review Time: {timestamp}")

    print("\n🔍 Validating with GDPR guardrails...")
    results = validate_with_gdpr(output)

    print(f"\n✅ GDPR Validation Results:")
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        article = result.metadata.get("article", "Unknown")
        print(f"  {status} - {article}")
        print(f"       {result.details}")

    all_passed = all(r.passed for r in results)
    if all_passed:
        print("\n🎉 All GDPR guardrails passed! High-risk decision validated.")
    else:
        print("\n❌ GDPR validation failed!")


# =============================================================================
# Demo 5: GDPR Violation - High-Risk without Review (BLOCKED)
# =============================================================================

def demo_5_gdpr_violation():
    """
    Demo 5: GDPR Violation - High-Risk without Human Review

    Shows GDPR Article 22 blocking high-risk decision without review.
    """
    print_header("DEMO 5: GDPR Violation - High-Risk without Review (BLOCKED)")

    print("Creating high-risk decision WITHOUT human review...")
    from neutron.compliance.sentinel import AgentOutput
    from neutron.compliance.auditors import gdpr_art22_human_oversight_guardrail

    output = AgentOutput(
        content="Credit card application DENIED",
        metadata={
            "risk_level": "high",  # High risk
            "human_reviewed": False,  # ❌ MISSING HUMAN REVIEW
        }
    )

    print(f"\n📋 Decision metadata:")
    print(f"  Risk Level: high")
    print(f"  Human Reviewed: ❌ No")

    print("\n🔍 Attempting to enforce GDPR Article 22...")

    try:
        enforced = gdpr_art22_human_oversight_guardrail.enforce(output)
        print("\n⚠️  Unexpectedly passed (should have been blocked)")
    except ComplianceViolation as e:
        print(f"\n✅ BLOCKED by GDPR Article 22!")
        print(f"\n❌ Violation Details:")
        print(f"  Guardrail: {e.guardrail.name}")
        print(f"  Regulation: {e.guardrail.regulation}")
        print(f"  Severity: {e.guardrail.severity}")
        print(f"  Reason: {e.result.details}")
        print(f"\n🚫 Output delivery prevented - compliance violation!")


# =============================================================================
# Demo 6: Customer Data Erasure (GDPR Article 17)
# =============================================================================

async def demo_6_gdpr_erasure():
    """
    Demo 6: Customer Data Erasure

    Shows GDPR Article 17 "Right to be Forgotten" implementation.
    """
    print_header("DEMO 6: Customer Data Erasure (GDPR Article 17)")

    print("Creating memory store for erasure demo...")
    try:
        memory_store = MemoryStore()
        print("✅ Connected to memory store\n")
    except Exception as e:
        print(f"⚠️  Memory store unavailable: {e}")
        print("   (Skipping demo - requires PostgreSQL with pgvector)\n")
        return

    print("📝 Storing customer data in memory...")
    customer_id = "customer_erasure_demo"

    memories = [
        "Customer inquiry about mortgage rates",
        "Customer preferences: low-risk investments",
        "Customer contact: email preferred",
    ]

    for i, content in enumerate(memories):
        memory_store.store(
            agent_id="demo_agent",
            content=content,
            embedding=create_mock_embedding(seed=300 + i),
            metadata={"customer_id": customer_id},
            importance_score=0.7
        )
        print(f"  ✓ Stored: {content}")

    print(f"\n🗑️  Customer requests data erasure (GDPR Article 17)...")

    from neutron.compliance.auditors import GDPRErasureHandler

    handler = GDPRErasureHandler(memory_store=memory_store)
    result = handler.erase_customer_data(customer_id)

    print(f"\n✅ Erasure Complete:")
    print(f"  Customer ID: {result['customer_id']}")
    print(f"  Memories Deleted: {result['deleted_memories']}")
    print(f"  Audit ID: {result['audit_id']}")
    print(f"  Status: {result['status']}")
    print(f"\n🎉 Customer data successfully erased!")


# =============================================================================
# Demo 7: Full NEXUS Workflow - Complete Integration
# =============================================================================

async def demo_7_full_nexus_workflow():
    """
    Demo 7: Full NEXUS Workflow

    Complete integration showing CORTEX + SYNAPSE + GDPR working together.
    """
    print_header("DEMO 7: Full NEXUS Workflow - Complete Integration")

    print("🚀 Initializing NEXUS system...")
    print("  - CORTEX: Multi-agent orchestration")
    print("  - SYNAPSE: Long-term memory")
    print("  - GDPR: Compliance guardrails\n")

    try:
        memory_store = MemoryStore()
        print("✅ Memory store connected\n")
    except Exception as e:
        print(f"⚠️  Memory store unavailable: {e}")
        print("   (Running demo without persistent memory)\n")
        memory_store = None

    print("👥 Creating multi-agent swarm...")
    swarm = create_nexus_swarm(
        agent_configs=[
            {"agent_id": "risk_analyst", "name": "Risk Analyst AI", "risk_level": "low"},
            {"agent_id": "compliance_expert", "name": "Compliance Expert AI", "risk_level": "low"},
            {"agent_id": "portfolio_advisor", "name": "Portfolio Advisor AI", "risk_level": "low"},
        ],
        memory_store=memory_store,
        enable_gdpr=True,
        consensus_strategy="majority_vote"
    )
    print(f"  ✓ Created swarm with {len(swarm.agents)} agents\n")

    if memory_store:
        print("📝 Pre-populating customer memory...")
        customer_id = "customer_nexus_demo"
        past_memories = [
            "Customer has conservative investment strategy",
            "Customer priority: capital preservation over growth",
            "Customer timeline: 15-year investment horizon",
        ]

        for i, content in enumerate(past_memories):
            memory_store.store(
                agent_id="nexus_swarm",
                content=content,
                embedding=create_mock_embedding(seed=400 + i),
                metadata={"customer_id": customer_id},
                importance_score=0.8
            )
            print(f"  ✓ {content}")

    print("\n📋 Creating task: Portfolio recommendation...")
    task = Task(
        task_id="nexus_portfolio_task",
        description="Generate portfolio allocation recommendation",
        input_data={
            "query_embedding": create_mock_embedding(seed=400),
            "output_embedding": create_mock_embedding(seed=500),
        },
        metadata={"risk_level": "low"},  # Low risk = no human review needed
        consensus_strategy="majority_vote"
    )

    print("\n🔄 Executing NEXUS workflow...")
    print("  1. Agents retrieve relevant memories (SYNAPSE)")
    print("  2. Agents execute task with memory context")
    print("  3. Agents reach consensus (CORTEX)")
    print("  4. Validate with GDPR guardrails")
    print("  5. Store consensus as new memory")

    result = await swarm.execute_with_memory(
        task=task,
        customer_id=customer_id if memory_store else None,
        retrieve_k=3,
        human_reviewer_id=None  # Low risk doesn't need review
    )

    print(f"\n✅ NEXUS Workflow Complete!")
    print(f"\n📊 Consensus Result:")
    print(f"  Output: {result['consensus_output']}")
    print(f"  Confidence: {result['consensus_confidence']:.2f}")
    print(f"  Agreement: {result['agreement_score']:.2f}")

    print(f"\n🔒 Compliance Status:")
    print(f"  GDPR Enabled: {result['metadata']['gdpr_enabled']}")
    print(f"  Compliance Passed: {'✅ Yes' if result['compliance_passed'] else '❌ No'}")

    if result['validation_results']:
        print(f"\n  GDPR Validation:")
        for validation in result['validation_results']:
            status = "✅" if validation.passed else "❌"
            article = validation.metadata.get("article", "Unknown")
            print(f"    {status} {article}")

    print(f"\n💾 Memory:")
    print(f"  Memory ID: {result['memory_id']}")
    print(f"  Customer ID: {result['metadata']['customer_id']}")

    print(f"\n🎯 Agent Consensus:")
    for i, agent_result in enumerate(result['individual_results'], 1):
        print(f"  Agent {i}: {agent_result.metadata.get('agent_name')}")
        print(f"    - Memories used: {agent_result.metadata.get('memory_count', 0)}")
        print(f"    - Confidence: {agent_result.confidence:.2f}")

    if memory_store and customer_id:
        print(f"\n🧹 Cleaning up demo data...")
        deleted = memory_store.delete_by_customer(customer_id)
        print(f"  ✓ Deleted {deleted} memories")

    print(f"\n🎉 Full NEXUS integration demonstrated successfully!")


# =============================================================================
# Main Demo Runner
# =============================================================================

async def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("  NEXUS PHASE 2 DEMONSTRATION")
    print("  Multi-Agent Orchestration with Memory & Compliance")
    print("=" * 70)
    print("\nPhase 2 Components:")
    print("  ✅ CORTEX  - Multi-agent consensus algorithms")
    print("  ✅ SYNAPSE - Long-term memory with semantic search")
    print("  ✅ GDPR    - EU compliance guardrails (Articles 22, 15, 17)")
    print("\n" + "=" * 70)

    demos = [
        ("CORTEX Only", demo_1_cortex_consensus, False),
        ("SYNAPSE Integration", demo_2_memory_enabled_agent, True),
        ("GDPR Low-Risk", demo_3_gdpr_low_risk, False),
        ("GDPR High-Risk (Compliant)", demo_4_gdpr_high_risk_compliant, False),
        ("GDPR Violation (Blocked)", demo_5_gdpr_violation, False),
        ("GDPR Erasure", demo_6_gdpr_erasure, True),
        ("Full NEXUS Workflow", demo_7_full_nexus_workflow, True),
    ]

    for i, (name, demo_func, is_async) in enumerate(demos, 1):
        print(f"\n\n{'█' * 70}")
        print(f"  Demo {i}/{len(demos)}: {name}")
        print(f"{'█' * 70}\n")

        input(f"Press Enter to run Demo {i}...")

        try:
            if is_async:
                await demo_func()
            else:
                demo_func()
        except Exception as e:
            print(f"\n❌ Demo error: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "─" * 70)

    print("\n" + "=" * 70)
    print("  ALL DEMOS COMPLETE")
    print("=" * 70)
    print("\n🎉 Phase 2 Integration Successfully Demonstrated!")
    print("\nKey Achievements:")
    print("  ✅ Multi-agent consensus (CORTEX)")
    print("  ✅ Semantic memory search (SYNAPSE)")
    print("  ✅ GDPR compliance enforcement")
    print("  ✅ Complete NEXUS integration")
    print("\nNext: Phase 3 - ORACLE (Explainability) + EU AI Act")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
