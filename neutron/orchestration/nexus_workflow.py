"""
NEXUS Integrated Workflow - Phase 2 Complete

Combines CORTEX (Multi-Agent), SYNAPSE (Memory), and GDPR (Compliance)
into unified workflows for production-grade AI agent orchestration.

Architecture:
┌─────────────────────────────────────────────────────────┐
│                    NEXUS Workflow                       │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │ CORTEX   │───▶│ SYNAPSE  │───▶│  GDPR    │         │
│  │Multi-Agent│    │ Memory   │    │Compliance│         │
│  └──────────┘    └──────────┘    └──────────┘         │
│       │               │                 │              │
│       ▼               ▼                 ▼              │
│  Consensus      Long-term         Validated           │
│   Output         Context           Output             │
└─────────────────────────────────────────────────────────┘

Example:
    >>> # Create memory-enabled agent swarm
    >>> swarm = create_nexus_swarm(
    ...     agent_configs=[...],
    ...     memory_store=MemoryStore(),
    ...     enable_gdpr=True
    ... )
    >>>
    >>> # Execute task with memory and compliance
    >>> result = await swarm.execute_with_memory(
    ...     task=Task(...),
    ...     customer_id="customer_123"
    ... )
"""

from typing import List, Optional, Dict, Any, Protocol
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import numpy as np

# CORTEX - Multi-Agent Orchestration
from neutron.orchestration.cortex import (
    Agent,
    AgentSwarm,
    Task,
    AgentResult,
    SwarmResult,
    ConsensusStrategy,
    ConsensusEngine,
)

# SYNAPSE - Long-term Memory
from neutron.memory import (
    MemoryStore,
    Memory,
    MemorySearchResult,
)

# GDPR - Compliance Guardrails
from neutron.compliance.sentinel import (
    AgentOutput,
    ComplianceViolation,
)
from neutron.compliance.auditors import (
    GDPR_GUARDRAILS,
    gdpr_art22_human_oversight_guardrail,
    validate_with_gdpr,
    GDPRErasureHandler,
)


# =============================================================================
# Memory-Enabled Agent
# =============================================================================

class MemoryEnabledAgent(Protocol):
    """
    Protocol for agents with memory capabilities

    Agents implementing this protocol can store and retrieve memories
    from SYNAPSE for context-aware decision making.
    """

    agent_id: str

    async def execute_with_memory(
        self,
        task: Task,
        memory_store: MemoryStore,
        retrieve_k: int = 5
    ) -> AgentResult:
        """Execute task using memory context"""
        ...


@dataclass
class NexusAgent:
    """
    Memory-enabled agent with compliance guardrails

    Combines:
    - Agent execution (CORTEX)
    - Memory storage/retrieval (SYNAPSE)
    - Compliance validation (GDPR)

    Attributes:
        agent_id: Unique agent identifier
        name: Human-readable agent name
        memory_store: SYNAPSE memory store
        enable_gdpr: Whether to enforce GDPR compliance
        risk_level: Decision risk level (low/medium/high)
    """
    agent_id: str
    name: str
    memory_store: Optional[MemoryStore] = None
    enable_gdpr: bool = True
    risk_level: str = "low"

    # Mock execution function (replace with real LLM/model)
    execution_function: Any = None

    async def execute(self, task: Task) -> AgentResult:
        """
        Execute task without memory (standard CORTEX agent)

        Args:
            task: Task to execute

        Returns:
            AgentResult with output and confidence
        """
        # This would call actual LLM/model in production
        if self.execution_function:
            output = await self.execution_function(task)
        else:
            output = f"[{self.name}] Processed: {task.description}"

        return AgentResult(
            agent_id=self.agent_id,
            output=output,
            confidence=0.85,
            metadata={"agent_name": self.name}
        )

    async def execute_with_memory(
        self,
        task: Task,
        customer_id: Optional[str] = None,
        retrieve_k: int = 5,
        store_result: bool = True
    ) -> AgentResult:
        """
        Execute task with memory context from SYNAPSE

        Process:
        1. Retrieve relevant memories from SYNAPSE
        2. Include memory context in task execution
        3. Execute task with enriched context
        4. Store result as new memory (if store_result=True)
        5. Validate with GDPR guardrails (if enabled)

        Args:
            task: Task to execute
            customer_id: Customer ID for memory filtering
            retrieve_k: Number of memories to retrieve
            store_result: Whether to store result as new memory

        Returns:
            AgentResult with memory-enriched output
        """
        context_memories = []

        # 1. Retrieve relevant memories
        if self.memory_store and task.input_data.get("query_embedding"):
            memory_results = self.memory_store.search(
                query_embedding=task.input_data["query_embedding"],
                agent_id=self.agent_id,
                top_k=retrieve_k,
                similarity_threshold=0.7
            )
            context_memories = memory_results

            # Log memory access for importance updates
            for mem_result in memory_results:
                self.memory_store.log_access(
                    memory_id=mem_result.memory.id,
                    agent_id=self.agent_id,
                    context={"task": task.description}
                )

        # 2. Build enriched context
        memory_context = "\n".join([
            f"- {mem.memory.content} (similarity: {mem.similarity:.2f})"
            for mem in context_memories
        ])

        # 3. Execute with context
        if self.execution_function:
            output = await self.execution_function(task, memory_context)
        else:
            output = f"[{self.name}] Processed '{task.description}' with {len(context_memories)} memories"

        result = AgentResult(
            agent_id=self.agent_id,
            output=output,
            confidence=0.90,  # Higher confidence with memory context
            metadata={
                "agent_name": self.name,
                "memory_count": len(context_memories),
                "customer_id": customer_id,
            }
        )

        # 4. Store result as new memory
        if store_result and self.memory_store and task.input_data.get("output_embedding"):
            self.memory_store.store(
                agent_id=self.agent_id,
                content=output,
                embedding=task.input_data["output_embedding"],
                metadata={
                    "task": task.description,
                    "customer_id": customer_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                importance_score=0.7
            )

        return result


# =============================================================================
# NEXUS Swarm - Integrated Multi-Agent with Memory & Compliance
# =============================================================================

@dataclass
class NexusSwarm:
    """
    Multi-agent swarm with memory and compliance

    Combines CORTEX consensus, SYNAPSE memory, and GDPR compliance
    into a unified workflow for production-grade AI orchestration.

    Attributes:
        agents: List of NexusAgent instances
        memory_store: Shared SYNAPSE memory store
        enable_gdpr: Whether to enforce GDPR compliance
        consensus_strategy: CORTEX consensus strategy
    """
    agents: List[NexusAgent]
    memory_store: MemoryStore
    enable_gdpr: bool = True
    consensus_strategy: ConsensusStrategy = "majority_vote"

    async def execute_with_memory(
        self,
        task: Task,
        customer_id: Optional[str] = None,
        retrieve_k: int = 5,
        human_reviewer_id: Optional[str] = None,
        review_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute task with full NEXUS integration

        Complete workflow:
        1. Each agent retrieves relevant memories (SYNAPSE)
        2. Agents execute task with memory context
        3. Reach consensus on outputs (CORTEX)
        4. Validate consensus with GDPR guardrails
        5. Store consensus as new memory (SYNAPSE)
        6. Return validated result

        Args:
            task: Task to execute
            customer_id: Customer ID for memory/compliance
            retrieve_k: Number of memories to retrieve
            human_reviewer_id: For GDPR Article 22 compliance
            review_timestamp: For GDPR Article 22 compliance

        Returns:
            Dict with consensus output, validation, and metadata
        """
        # 1. Execute all agents with memory
        individual_results = await asyncio.gather(*[
            agent.execute_with_memory(
                task=task,
                customer_id=customer_id,
                retrieve_k=retrieve_k,
                store_result=False  # Store consensus, not individual
            )
            for agent in self.agents
        ])

        # 2. Reach consensus (CORTEX)
        consensus_output, consensus_confidence, agreement_score = (
            ConsensusEngine.apply_strategy(
                results=individual_results,
                strategy=self.consensus_strategy
            )
        )

        # 3. Build GDPR-compliant metadata
        risk_level = task.metadata.get("risk_level", "low")
        gdpr_metadata = {
            "risk_level": risk_level,
            "data_access_enabled": True,
            "data_categories": ["agent_outputs", "consensus_results"],
            "retention_period": "90 days",
            "export_format": "JSON",
            "processes_personal_data": customer_id is not None,
            "erasure_supported": True,
            "erasure_endpoint": "/api/v1/customers/{id}/delete",
            "customer_id": customer_id,
        }

        # Add human oversight for high-risk decisions (GDPR Article 22)
        if risk_level in ["high", "medium"]:
            gdpr_metadata.update({
                "human_reviewed": human_reviewer_id is not None,
                "reviewer_id": human_reviewer_id,
                "review_timestamp": review_timestamp or datetime.utcnow().isoformat()
            })

        # 4. Create AgentOutput for GDPR validation
        agent_output = AgentOutput(
            content=str(consensus_output),
            metadata=gdpr_metadata
        )

        # 5. Validate with GDPR guardrails
        validation_results = []
        compliance_passed = True

        if self.enable_gdpr:
            validation_results = validate_with_gdpr(agent_output)

            # Check if any blocking guardrails failed
            for result in validation_results:
                if not result.passed:
                    # Article 22 is blocking
                    if "Article 22" in result.metadata.get("article", ""):
                        raise ComplianceViolation(
                            guardrail=gdpr_art22_human_oversight_guardrail,
                            result=result
                        )
                    compliance_passed = False

        # 6. Store consensus as new memory
        if task.input_data.get("output_embedding"):
            memory_id = self.memory_store.store(
                agent_id="nexus_swarm",
                content=str(consensus_output),
                embedding=task.input_data["output_embedding"],
                metadata={
                    "task": task.description,
                    "customer_id": customer_id,
                    "consensus_strategy": self.consensus_strategy,
                    "agreement_score": agreement_score,
                    "agent_count": len(self.agents),
                    "risk_level": risk_level,
                },
                importance_score=agreement_score,  # Higher agreement = higher importance
                memory_type="semantic"
            )
        else:
            memory_id = None

        # 7. Return complete result
        return {
            "consensus_output": consensus_output,
            "consensus_confidence": consensus_confidence,
            "agreement_score": agreement_score,
            "individual_results": individual_results,
            "compliance_passed": compliance_passed,
            "validation_results": validation_results,
            "memory_id": memory_id,
            "metadata": {
                "customer_id": customer_id,
                "risk_level": risk_level,
                "agent_count": len(self.agents),
                "consensus_strategy": self.consensus_strategy,
                "gdpr_enabled": self.enable_gdpr,
            }
        }

    async def erase_customer_data(self, customer_id: str) -> Dict[str, Any]:
        """
        GDPR Article 17 - Right to Erasure

        Delete all memories and data for a customer.

        Args:
            customer_id: Customer ID to erase

        Returns:
            Erasure confirmation with deletion count
        """
        handler = GDPRErasureHandler(memory_store=self.memory_store)
        return handler.erase_customer_data(customer_id)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_nexus_swarm(
    agent_configs: List[Dict[str, Any]],
    memory_store: Optional[MemoryStore] = None,
    enable_gdpr: bool = True,
    consensus_strategy: ConsensusStrategy = "majority_vote"
) -> NexusSwarm:
    """
    Create a NEXUS swarm with memory and compliance

    Args:
        agent_configs: List of agent configurations
            Each config should have: agent_id, name, risk_level
        memory_store: SYNAPSE memory store (creates new if None)
        enable_gdpr: Enable GDPR compliance guardrails
        consensus_strategy: CORTEX consensus strategy

    Returns:
        NexusSwarm ready for execution

    Example:
        >>> swarm = create_nexus_swarm(
        ...     agent_configs=[
        ...         {"agent_id": "agent_1", "name": "Analyst", "risk_level": "low"},
        ...         {"agent_id": "agent_2", "name": "Expert", "risk_level": "low"},
        ...     ],
        ...     enable_gdpr=True
        ... )
    """
    if memory_store is None:
        memory_store = MemoryStore()

    agents = [
        NexusAgent(
            agent_id=config["agent_id"],
            name=config["name"],
            memory_store=memory_store,
            enable_gdpr=enable_gdpr,
            risk_level=config.get("risk_level", "low")
        )
        for config in agent_configs
    ]

    return NexusSwarm(
        agents=agents,
        memory_store=memory_store,
        enable_gdpr=enable_gdpr,
        consensus_strategy=consensus_strategy
    )


async def execute_nexus_workflow(
    task_description: str,
    agent_configs: List[Dict[str, Any]],
    query_embedding: np.ndarray,
    output_embedding: np.ndarray,
    customer_id: Optional[str] = None,
    risk_level: str = "low",
    human_reviewer_id: Optional[str] = None,
    consensus_strategy: ConsensusStrategy = "majority_vote",
    enable_gdpr: bool = True
) -> Dict[str, Any]:
    """
    Execute complete NEXUS workflow (one-shot convenience function)

    This is a high-level function that:
    1. Creates a NexusSwarm
    2. Creates a Task
    3. Executes with memory and compliance
    4. Returns validated result

    Args:
        task_description: Task description
        agent_configs: Agent configurations
        query_embedding: Embedding for memory retrieval
        output_embedding: Embedding for storing result
        customer_id: Customer ID for memory/compliance
        risk_level: Decision risk level (low/medium/high)
        human_reviewer_id: For high-risk GDPR compliance
        consensus_strategy: CORTEX consensus strategy
        enable_gdpr: Enable GDPR compliance

    Returns:
        Complete result with consensus, compliance, and memory

    Example:
        >>> result = await execute_nexus_workflow(
        ...     task_description="Analyze customer risk profile",
        ...     agent_configs=[
        ...         {"agent_id": "risk_analyst", "name": "Risk Analyst"},
        ...         {"agent_id": "compliance_expert", "name": "Compliance Expert"},
        ...     ],
        ...     query_embedding=embed("customer risk analysis"),
        ...     output_embedding=embed("customer risk profile"),
        ...     customer_id="customer_123",
        ...     risk_level="medium",
        ...     human_reviewer_id="reviewer_001"
        ... )
    """
    # Create swarm
    swarm = create_nexus_swarm(
        agent_configs=agent_configs,
        enable_gdpr=enable_gdpr,
        consensus_strategy=consensus_strategy
    )

    # Create task
    task = Task(
        task_id=f"nexus_task_{datetime.utcnow().timestamp()}",
        description=task_description,
        input_data={
            "query_embedding": query_embedding,
            "output_embedding": output_embedding,
        },
        metadata={
            "risk_level": risk_level,
            "customer_id": customer_id,
        },
        consensus_strategy=consensus_strategy
    )

    # Execute with full integration
    result = await swarm.execute_with_memory(
        task=task,
        customer_id=customer_id,
        human_reviewer_id=human_reviewer_id
    )

    return result


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core classes
    "NexusAgent",
    "NexusSwarm",

    # Convenience functions
    "create_nexus_swarm",
    "execute_nexus_workflow",
]
