"""
Temporal workflows, workers, and multi-agent orchestration (CORTEX + NEXUS)
"""

from neutron.orchestration.workflows import (
    start_adaptive_pipeline,
    AdaptiveMLPipelineWorkflow,
    EnsembleTrainingWorkflow,
    AdaptiveMLPipelineWithQueries,
)

from neutron.orchestration.cortex import (
    Agent,
    AgentSwarm,
    Task,
    AgentResult,
    SwarmResult,
    ConsensusStrategy,
    ConsensusEngine,
    create_swarm,
)

from neutron.orchestration.nexus_workflow import (
    NexusAgent,
    NexusSwarm,
    create_nexus_swarm,
    execute_nexus_workflow,
)

__all__ = [
    # Temporal workflows
    "start_adaptive_pipeline",
    "AdaptiveMLPipelineWorkflow",
    "EnsembleTrainingWorkflow",
    "AdaptiveMLPipelineWithQueries",
    # CORTEX multi-agent
    "Agent",
    "AgentSwarm",
    "Task",
    "AgentResult",
    "SwarmResult",
    "ConsensusStrategy",
    "ConsensusEngine",
    "create_swarm",
    # NEXUS integrated workflow
    "NexusAgent",
    "NexusSwarm",
    "create_nexus_swarm",
    "execute_nexus_workflow",
]
