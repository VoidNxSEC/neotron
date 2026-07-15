#!/usr/bin/env python3
"""
Neutron Swarm Demo (Standalone)
Verifies the Logic of Agents and Consensus without Temporal middleware.
"""
import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.getcwd())

from neutron.agents.cortex import Agent, AgentSwarm, ConsensusStrategy
from neutron.memory.episodic import EpisodicMemory

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("demo_swarm")


async def main():
    print("🚀 Initializing Neutron Agent Swarm (Real Infrastructure)...")

    # 1. Setup Memory (Stubbed for demo if Postgres not available, or real if it is)
    try:
        memory = EpisodicMemory()
        print("✅ Synapse Memory initialized (PostgreSQL/pgvector)")
    except Exception as e:
        print(
            f"⚠️  Synapse Memory skipped (DB connection failed: {e}) - Proceeding with In-Memory Agents"
        )

    # 2. Initialize Agents
    agents = [
        Agent(name="Architect", role="design"),
        Agent(name="Engineer", role="implementation"),
        Agent(name="Security", role="audit"),
    ]

    print(f"👥 Created {len(agents)} Agents: {[a.name for a in agents]}")

    # 3. Initialize Swarm with Consensus
    swarm = AgentSwarm(agents, consensus_strategy=ConsensusStrategy.MAJORITY_VOTE)

    task = {
        "id": "task-001",
        "description": "Analyze security risks of exposed Docker socket",
        "context": "Production environment",
    }

    print(f"\n📨 Broadcasting Task: {task['description']}")

    # 4. Execute
    result = await swarm.broadcast_task(task)

    # 5. Report
    print("\n📊 Swarm Results:")
    for res in result["individual_results"]:
        print(f"  - [{res['agent']}] Confidence: {res['confidence']}")

    print(f"\n🧠 Consensus Decision: {result['consensus']['decision']}")
    print(f"   Confidence: {result['consensus'].get('confidence')}")

    if result["consensus"]["decision"]:
        print("\n✅ DEMO PASSED: Agents successfully coordinated and reached consensus.")
    else:
        print("\n❌ DEMO FAILED: No consensus reached.")


if __name__ == "__main__":
    asyncio.run(main())
