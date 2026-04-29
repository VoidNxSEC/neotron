#!/usr/bin/env python3
"""
Neutron Self-Audit (Dogfooding)
Uses the Cortex Agent Swarm to audit the project's own configuration files.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from neutron.agents.cortex import Agent, AgentSwarm, ConsensusStrategy

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")


async def main():
    print("🤖 Neutron Compliance Agent (Self-Audit Mode)")
    print("---------------------------------------------")

    # 1. Load Artefacts to Audit
    # We load the actual content of key files we created
    files_to_audit = {
        "spectre_flake": (
            Path("../spectre/flake.nix").read_text()
            if Path("../spectre/flake.nix").exists()
            else "MISSING"
        ),
        "spectre_proxy": (
            Path("../spectre/crates/spectre-proxy/src/main.rs").read_text()
            if Path("../spectre/crates/spectre-proxy/src/main.rs").exists()
            else "MISSING"
        ),
        "neutron_flake": Path("flake.nix").read_text(),
    }

    # 2. Define Agents specialized for Audit
    # Note: Agent class from cortex.py currently only supports (name, role)
    # The 'description' was a logic mismatch, so we document purpose in comments.
    agents = [
        Agent(name="SecurityAuditor", role="audit"),
        Agent(name="NixCompliance", role="config"),
        Agent(name="ArchitectureReview", role="design"),
    ]

    # 3. Initialize Swarm
    swarm = AgentSwarm(agents, consensus_strategy=ConsensusStrategy.MAJORITY_VOTE)

    # 4. Construct the Task
    # We inject the file content into the task context for the LLM (simulated here) to analyze
    task_desc = """
    AUDIT REQUEST: Verify Critical Infrastructure Code.
    
    1. Check 'spectre_proxy' for:
       - Hardcoded secrets (FAIL)
       - Authentication middleware presence (PASS)
       - TLS/mTLS configuration (PASS)
    
    2. Check 'spectre_flake' for:
       - 'sops-nix' input presence (PASS)
       - Build environment security (PASS)
    """

    print("\n📨 Broadcasting Audit Task to Swarm...")

    # 5. Execute
    # In a real run, this would send the file content to the LLM.
    # Here we simulate the agent finding the keywords we implemented.
    result = await swarm.broadcast_task(
        {
            "id": "audit-final-001",
            "description": task_desc,
            "context": files_to_audit,  # Passing real file content
        }
    )

    # 6. Report
    print("\n📊 Audit Results:")
    for res in result["individual_results"]:
        print(f"  [{res['agent']}] Verdict: {res['content']}")  # Using simulated result from stub

    print(f"\n🏆 Final Consensus: {result['consensus']['decision']}")


if __name__ == "__main__":
    asyncio.run(main())
