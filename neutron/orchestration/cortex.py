"""
CORTEX - Multi-Agent Orchestration System

Coordinates multiple specialist agents to reach consensus on complex tasks.

Philosophy:
    Many minds are better than one. CORTEX enables agent swarms to collaborate,
    each bringing specialized expertise, with democratic consensus protocols.

Key Features:
    - Agent swarm coordination
    - Multiple consensus strategies (majority vote, weighted average, etc.)
    - Task decomposition and delegation
    - Result aggregation and validation
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol, Dict, Callable
from enum import Enum
from datetime import datetime
import asyncio
from collections import Counter
import statistics


# =============================================================================
# Data Models
# =============================================================================

class ConsensusStrategy(Enum):
    """Consensus strategies for aggregating agent results"""
    MAJORITY_VOTE = "majority_vote"        # Most common output wins
    WEIGHTED_AVERAGE = "weighted_average"  # Weighted by confidence scores
    UNANIMOUS = "unanimous"                # All agents must agree
    BEST_CONFIDENCE = "best_confidence"    # Highest confidence wins
    MEAN_CONFIDENCE = "mean_confidence"    # Average of numeric outputs weighted by confidence


@dataclass
class Task:
    """
    Task to be executed by agent swarm

    Attributes:
        type: Task type identifier (e.g., "classification", "regression")
        input: Input data for the task
        consensus_strategy: How to aggregate results
        metadata: Additional task metadata
        require_all_agents: Whether all agents must respond
        timeout_seconds: Maximum time to wait for responses
    """
    type: str
    input: Any
    consensus_strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY_VOTE
    metadata: Optional[Dict[str, Any]] = None
    require_all_agents: bool = False
    timeout_seconds: float = 30.0


@dataclass
class AgentResult:
    """
    Result from individual agent

    Attributes:
        agent_id: Unique identifier for the agent
        output: Agent's output/prediction
        confidence: Confidence score (0.0-1.0)
        explanation: Human-readable explanation of the decision
        metadata: Additional result metadata
        processing_time_ms: Time taken to process (milliseconds)
    """
    agent_id: str
    output: Any
    confidence: float
    explanation: str
    metadata: Optional[Dict[str, Any]] = None
    processing_time_ms: float = 0.0

    def __post_init__(self):
        """Validate confidence score"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class SwarmResult:
    """
    Aggregated result from agent swarm

    Attributes:
        task: Original task
        consensus_output: Final consensus output
        consensus_confidence: Confidence in consensus
        individual_results: Results from each agent
        consensus_strategy: Strategy used for consensus
        agreement_score: How much agents agreed (0.0-1.0)
        timestamp: When consensus was reached
    """
    task: Task
    consensus_output: Any
    consensus_confidence: float
    individual_results: List[AgentResult]
    consensus_strategy: ConsensusStrategy
    agreement_score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def num_agents(self) -> int:
        """Number of agents that participated"""
        return len(self.individual_results)

    @property
    def avg_confidence(self) -> float:
        """Average confidence across all agents"""
        if not self.individual_results:
            return 0.0
        return statistics.mean(r.confidence for r in self.individual_results)


# =============================================================================
# Agent Protocol
# =============================================================================

class Agent(Protocol):
    """
    Protocol for agents in swarm

    All agents must implement this interface to participate in CORTEX swarms.
    """

    agent_id: str

    async def execute(self, task: Task) -> AgentResult:
        """
        Execute task and return result

        Args:
            task: Task to execute

        Returns:
            AgentResult with output, confidence, and explanation
        """
        ...


# =============================================================================
# Consensus Algorithms
# =============================================================================

class ConsensusEngine:
    """
    Consensus engine for aggregating agent results

    Implements various consensus strategies for different task types.
    """

    @staticmethod
    def majority_vote(results: List[AgentResult]) -> tuple[Any, float, float]:
        """
        Majority vote consensus - most common output wins

        Args:
            results: List of agent results

        Returns:
            Tuple of (consensus_output, consensus_confidence, agreement_score)
        """
        if not results:
            raise ValueError("Cannot compute consensus with no results")

        # Count votes
        vote_counts = Counter(r.output for r in results)
        consensus_output = vote_counts.most_common(1)[0][0]

        # Calculate agreement score
        num_agreeing = vote_counts[consensus_output]
        agreement_score = num_agreeing / len(results)

        # Calculate consensus confidence (average of agreeing agents)
        agreeing_results = [r for r in results if r.output == consensus_output]
        consensus_confidence = statistics.mean(r.confidence for r in agreeing_results)

        return consensus_output, consensus_confidence, agreement_score

    @staticmethod
    def weighted_average(results: List[AgentResult]) -> tuple[Any, float, float]:
        """
        Weighted average consensus - average weighted by confidence

        For numeric outputs only. Falls back to best_confidence for non-numeric.

        Args:
            results: List of agent results

        Returns:
            Tuple of (consensus_output, consensus_confidence, agreement_score)
        """
        if not results:
            raise ValueError("Cannot compute consensus with no results")

        # Check if outputs are numeric
        try:
            numeric_outputs = [float(r.output) for r in results]
        except (ValueError, TypeError):
            # Non-numeric outputs, fall back to best confidence
            return ConsensusEngine.best_confidence(results)

        # Calculate weighted average
        total_weight = sum(r.confidence for r in results)
        if total_weight == 0:
            # All confidences are 0, use simple average
            consensus_output = statistics.mean(numeric_outputs)
            consensus_confidence = 0.0
        else:
            weighted_sum = sum(float(r.output) * r.confidence for r in results)
            consensus_output = weighted_sum / total_weight
            consensus_confidence = statistics.mean(r.confidence for r in results)

        # Calculate agreement score (variance-based for numeric)
        variance = statistics.variance(numeric_outputs) if len(numeric_outputs) > 1 else 0
        # Lower variance = higher agreement
        agreement_score = 1.0 / (1.0 + variance) if variance > 0 else 1.0

        return consensus_output, consensus_confidence, agreement_score

    @staticmethod
    def unanimous(results: List[AgentResult]) -> tuple[Any, float, float]:
        """
        Unanimous consensus - all agents must agree

        Args:
            results: List of agent results

        Returns:
            Tuple of (consensus_output, consensus_confidence, agreement_score)

        Raises:
            ValueError: If agents don't unanimously agree
        """
        if not results:
            raise ValueError("Cannot compute consensus with no results")

        # Check if all outputs are the same
        outputs = [r.output for r in results]
        if len(set(outputs)) > 1:
            raise ValueError(
                f"Unanimous consensus failed: agents disagree. "
                f"Outputs: {outputs}"
            )

        consensus_output = outputs[0]
        consensus_confidence = statistics.mean(r.confidence for r in results)
        agreement_score = 1.0  # Perfect agreement

        return consensus_output, consensus_confidence, agreement_score

    @staticmethod
    def best_confidence(results: List[AgentResult]) -> tuple[Any, float, float]:
        """
        Best confidence consensus - highest confidence agent wins

        Args:
            results: List of agent results

        Returns:
            Tuple of (consensus_output, consensus_confidence, agreement_score)
        """
        if not results:
            raise ValueError("Cannot compute consensus with no results")

        # Find result with highest confidence
        best_result = max(results, key=lambda r: r.confidence)
        consensus_output = best_result.output
        consensus_confidence = best_result.confidence

        # Agreement score based on how many agree with best
        num_agreeing = sum(1 for r in results if r.output == consensus_output)
        agreement_score = num_agreeing / len(results)

        return consensus_output, consensus_confidence, agreement_score

    @staticmethod
    def mean_confidence(results: List[AgentResult]) -> tuple[Any, float, float]:
        """
        Mean with confidence weighting - for numeric outputs

        Similar to weighted_average but returns mean explicitly.

        Args:
            results: List of agent results

        Returns:
            Tuple of (consensus_output, consensus_confidence, agreement_score)
        """
        return ConsensusEngine.weighted_average(results)


# =============================================================================
# Agent Swarm
# =============================================================================

class AgentSwarm:
    """
    Coordinates multiple agents for consensus-based task execution

    Example:
        >>> swarm = AgentSwarm([agent_a, agent_b, agent_c])
        >>> result = await swarm.execute(Task(
        ...     type="classification",
        ...     input={"text": "Is this spam?"},
        ...     consensus_strategy=ConsensusStrategy.MAJORITY_VOTE
        ... ))
        >>> print(result.consensus_output)
    """

    def __init__(
        self,
        agents: List[Agent],
        name: Optional[str] = None
    ):
        """
        Initialize agent swarm

        Args:
            agents: List of agents to coordinate
            name: Optional name for the swarm
        """
        if not agents:
            raise ValueError("Swarm must have at least one agent")

        self.agents = agents
        self.name = name or f"swarm_{len(agents)}_agents"
        self._consensus_engine = ConsensusEngine()

    async def execute(self, task: Task) -> SwarmResult:
        """
        Execute task across swarm and reach consensus

        Args:
            task: Task to execute

        Returns:
            SwarmResult with consensus output and individual results

        Raises:
            ValueError: If consensus cannot be reached
            asyncio.TimeoutError: If agents don't respond in time
        """
        # Execute task with all agents in parallel
        individual_results = await self._execute_parallel(task)

        # Apply consensus strategy
        consensus_output, consensus_confidence, agreement_score = self._apply_consensus(
            individual_results,
            task.consensus_strategy
        )

        # Return swarm result
        return SwarmResult(
            task=task,
            consensus_output=consensus_output,
            consensus_confidence=consensus_confidence,
            individual_results=individual_results,
            consensus_strategy=task.consensus_strategy,
            agreement_score=agreement_score
        )

    async def _execute_parallel(self, task: Task) -> List[AgentResult]:
        """
        Execute task with all agents in parallel

        Args:
            task: Task to execute

        Returns:
            List of agent results

        Raises:
            asyncio.TimeoutError: If agents don't respond in time
        """
        # Create tasks for all agents
        agent_tasks = [
            asyncio.create_task(agent.execute(task))
            for agent in self.agents
        ]

        # Wait for all agents (with timeout)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*agent_tasks, return_exceptions=True),
                timeout=task.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"Agents did not respond within {task.timeout_seconds} seconds"
            )

        # Filter out exceptions and failed agents
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                if task.require_all_agents:
                    raise ValueError(
                        f"Agent {self.agents[i].agent_id} failed: {result}"
                    )
                # Skip failed agent if not required
                continue
            successful_results.append(result)

        if not successful_results:
            raise ValueError("All agents failed to produce results")

        if task.require_all_agents and len(successful_results) < len(self.agents):
            raise ValueError(
                f"Required all agents but only {len(successful_results)}/{len(self.agents)} responded"
            )

        return successful_results

    def _apply_consensus(
        self,
        results: List[AgentResult],
        strategy: ConsensusStrategy
    ) -> tuple[Any, float, float]:
        """
        Apply consensus strategy to aggregate results

        Args:
            results: List of agent results
            strategy: Consensus strategy to use

        Returns:
            Tuple of (consensus_output, consensus_confidence, agreement_score)
        """
        if strategy == ConsensusStrategy.MAJORITY_VOTE:
            return self._consensus_engine.majority_vote(results)
        elif strategy == ConsensusStrategy.WEIGHTED_AVERAGE:
            return self._consensus_engine.weighted_average(results)
        elif strategy == ConsensusStrategy.UNANIMOUS:
            return self._consensus_engine.unanimous(results)
        elif strategy == ConsensusStrategy.BEST_CONFIDENCE:
            return self._consensus_engine.best_confidence(results)
        elif strategy == ConsensusStrategy.MEAN_CONFIDENCE:
            return self._consensus_engine.mean_confidence(results)
        else:
            raise ValueError(f"Unknown consensus strategy: {strategy}")

    def add_agent(self, agent: Agent):
        """Add agent to swarm"""
        self.agents.append(agent)

    def remove_agent(self, agent_id: str):
        """Remove agent from swarm by ID"""
        self.agents = [a for a in self.agents if a.agent_id != agent_id]

    @property
    def num_agents(self) -> int:
        """Number of agents in swarm"""
        return len(self.agents)


# =============================================================================
# Utility Functions
# =============================================================================

def create_swarm(
    agents: List[Agent],
    name: Optional[str] = None
) -> AgentSwarm:
    """
    Convenience function to create agent swarm

    Args:
        agents: List of agents
        name: Optional swarm name

    Returns:
        AgentSwarm instance
    """
    return AgentSwarm(agents, name)
