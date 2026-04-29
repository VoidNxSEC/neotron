import os
import sys

# Add project root to path
sys.path.insert(0, os.getcwd())

print("🔍 Verifying Neutron Modules...")

try:
    print("  - Importing neutron.agents.cortex...", end=" ")
    from neutron.agents.cortex import AgentSwarm, ConsensusStrategy

    print("✅ OK")

    print("  - Importing neutron.agents.synapse...", end=" ")
    from neutron.agents.synapse import (
        SynapseMemory,
    )  # This was the stub, assuming name kept or updated logic

    # In my real implementation I used neutron.memory.episodic.
    # Let's check imports based on what I wrote.
    print("⚠️  (Namespace check required)")

    print("  - Importing neutron.memory.episodic...", end=" ")
    from neutron.memory.episodic import EpisodicMemory

    print("✅ OK")

    print("  - Importing neutron.orchestration.worker...", end=" ")
    from neutron.orchestration.worker import AgentCoordinationWorkflow

    print("✅ OK")

    print("\n🎉 All critical modules importable!")

except ImportError as e:
    print(f"\n❌ FAIL: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)
