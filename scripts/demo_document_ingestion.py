"""
Demo: Document Ingestion Pipeline
Demonstrates using Cortex Agent Swarm to ingest and analyze a compliance document.
"""

import asyncio
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("demo_ingestion")

from neutron.agents.cortex import AgentSwarm, ConsensusStrategy
from neutron.agents.document_agent import DocumentIngestionAgent


async def main():
    print("🚀 Neutron Document Ingestion Pipeline Demo")
    print("===========================================")

    # 1. Load Document
    doc_path = Path("docs/eu_ai_act_compliance.md")
    print(f"\n1. Loading document from: {doc_path}")

    if not doc_path.exists():
        # Fallback if file doesn't exist
        print("   File not found. Creating a dummy document for demo purposes...")
        doc_content = """
        # EU AI Act Compliance Notes
        
        The system MUST ensure that high-risk AI models log all decisions.
        Data MUST be kept in the EU region.
        Failure to comply may result in fines up to 35M EUR or 7% of global turnover.
        We need to implement a fallback mechanism for the semantic router immediately.
        """
        filename = "dummy_eu_ai_act.md"
    else:
        with open(doc_path, encoding="utf-8") as f:
            doc_content = f.read()
        filename = doc_path.name
        print(f"   Loaded {len(doc_content)} characters.")

    task = {
        "type": "document_analysis",
        "description": "Analyze the regulatory document for compliance requirements.",
        "data": {"filename": filename, "text": doc_content},
    }

    # 2. Initialize Agents
    print("\n2. Initializing Expert Swarm...")

    legal_agent = DocumentIngestionAgent(
        name="Legal-Alpha", role="Senior Regulatory Compliance Lawyer"
    )

    tech_agent = DocumentIngestionAgent(name="Tech-Beta", role="Principal Engineering Architect")

    risk_agent = DocumentIngestionAgent(name="Risk-Gamma", role="Chief Risk Officer")

    # 3. Create Swarm
    swarm = AgentSwarm(
        agents=[legal_agent, tech_agent, risk_agent],
        consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
    )
    print(f"   Swarm initialized with {len(swarm.agents)} agents.")

    # 4. Execute Analysis
    print("\n3. Broadcasting task to Swarm (Executing LLM calls...)")

    # In a real environment, this calls the configured LLM providers.
    # If the provider is mock/offline, it will handle it gracefully based on LLMClient setup.
    result = await swarm.broadcast_task(task)

    # 5. Display Results
    print("\n✅ Analysis Complete!")
    print("\n--- Consensus Decision ---")
    consensus = result.get("consensus", {})

    # Prettify the JSON if possible
    decision_str = consensus.get("decision", "{}")
    try:
        if isinstance(decision_str, str):
            parsed = json.loads(decision_str)
            print(json.dumps(parsed, indent=2))
        else:
            print(json.dumps(decision_str, indent=2))
    except json.JSONDecodeError:
        print(decision_str)

    print(f"\nConfidence: {consensus.get('confidence', 0.0):.2f}")

    print("\n--- Individual Results ---")
    for res in result.get("individual_results", []):
        print(f"Agent: {res.get('agent')}")
        print(f"Confidence: {res.get('confidence')}")
        print("-" * 20)


if __name__ == "__main__":
    # Ensure asyncio event loop runs
    asyncio.run(main())
