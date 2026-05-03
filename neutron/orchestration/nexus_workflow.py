"""
NexusAgent and create_nexus_swarm — high-level wrappers for demo and integration use.

NexusAgent: Agent with optional MemoryStore (PostgreSQL) and GDPR enforcement.
create_nexus_swarm: Factory that builds an AgentSwarm from config dicts.
"""

from __future__ import annotations

from typing import Any

from neutron.agents.cortex import Agent, AgentSwarm, ConsensusStrategy
from neutron.agents.synapse import SynapseMemory


class NexusAgent(Agent):
    """Agent with optional PostgreSQL MemoryStore and GDPR compliance flag."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        memory_store=None,
        enable_gdpr: bool = True,
        role: str = "nexus-agent",
        system_prompt: str | None = None,
        llm_client: Any | None = None,
    ):
        super().__init__(
            name=name,
            role=role,
            system_prompt=system_prompt,
            llm_client=llm_client,
            synapse=SynapseMemory(),
        )
        self.agent_id = agent_id
        self.memory_store = memory_store
        self.enable_gdpr = enable_gdpr


def create_nexus_swarm(
    agent_configs: list[dict],
    memory_store=None,
    enable_gdpr: bool = True,
    consensus_strategy: str = "majority_vote",
) -> AgentSwarm:
    """Build an AgentSwarm from a list of agent config dicts.

    Each dict must have 'agent_id' and 'name'. Optional: 'role', 'system_prompt'.
    """
    strategy_map = {
        "majority_vote": ConsensusStrategy.MAJORITY_VOTE,
        "best_confidence": ConsensusStrategy.WEIGHTED_CONFIDENCE,
        "weighted_average": ConsensusStrategy.WEIGHTED_CONFIDENCE,
        "unanimous": ConsensusStrategy.UNANIMOUS,
    }
    strategy = strategy_map.get(consensus_strategy, ConsensusStrategy.MAJORITY_VOTE)

    agents = [
        NexusAgent(
            agent_id=cfg["agent_id"],
            name=cfg["name"],
            role=cfg.get("role", "nexus-agent"),
            system_prompt=cfg.get("system_prompt"),
            memory_store=memory_store,
            enable_gdpr=enable_gdpr,
        )
        for cfg in agent_configs
    ]

    return AgentSwarm(agents=agents, default_strategy=strategy)
