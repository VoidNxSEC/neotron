"""
CORTEX Multi-Agent Orchestration System

Provides consensus-driven multi-agent coordination with support for:
- Multiple consensus strategies (majority vote, weighted average, unanimous, best confidence)
- Parallel agent execution with timeout support
- Partial failure tolerance
- Integrated ORACLE explainability
"""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConsensusStrategy(Enum):
    """Strategies for reaching consensus among multiple agents."""

    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    UNANIMOUS = "unanimous"
    BEST_CONFIDENCE = "best_confidence"


@dataclass
class Task:
    """A task to be executed by an agent swarm."""

    type: str
    input: dict
    consensus_strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY_VOTE
    timeout_seconds: float = 30.0
    require_all_agents: bool = False


@dataclass
class AgentResult:
    """Result from a single agent's execution."""

    agent_id: str
    output: Any
    confidence: float
    explanation: str = ""
    processing_time_ms: float = 0.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class SwarmResult:
    """Result from a swarm execution including consensus and individual results."""

    task: Task
    consensus_output: Any
    consensus_confidence: float
    individual_results: list[AgentResult]
    consensus_strategy: ConsensusStrategy
    agreement_score: float
    explanation: Any = None  # ExplanationResult | None, using Any to avoid import at class level

    @property
    def num_agents(self) -> int:
        """Number of agents that contributed results."""
        return len(self.individual_results)

    @property
    def avg_confidence(self) -> float:
        """Average confidence across all agent results."""
        if not self.individual_results:
            return 0.0
        return sum(r.confidence for r in self.individual_results) / len(self.individual_results)

    def generate_explanation(
        self,
        explanation_type=None,
        include_agent_reasoning: bool = True,
    ):
        """Generate an explanation for the swarm consensus decision.

        Args:
            explanation_type: The type of explanation to generate. Defaults to FEATURE_IMPORTANCE.
            include_agent_reasoning: Whether to include individual agent reasoning details.

        Returns:
            ExplanationResult with the generated explanation.
        """
        from neutron.reasoning.oracle import (
            ExplanationEvidence,
            ExplanationResult,
            ExplanationType,
        )

        if explanation_type is None:
            explanation_type = ExplanationType.FEATURE_IMPORTANCE

        decision = f"Swarm consensus: {self.consensus_output}"
        confidence = self.consensus_confidence

        if explanation_type == ExplanationType.FEATURE_IMPORTANCE:
            evidence = []
            for r in self.individual_results:
                evidence.append(
                    ExplanationEvidence(
                        feature=r.agent_id,
                        value=r.output,
                        importance=r.confidence,
                        description=f"Agent {r.agent_id} predicted '{r.output}' with confidence {r.confidence}",
                    )
                )
            # Sort by importance descending
            evidence.sort(key=lambda e: e.importance, reverse=True)

            reasoning = (
                f"Consensus reached for task '{self.task.type}' using {self.consensus_strategy.value} strategy. "
                f"{self.num_agents} agents participated with agreement score {self.agreement_score:.2f}."
            )

            result = ExplanationResult(
                decision=decision,
                explanation_type=explanation_type,
                confidence=confidence,
                evidence=evidence,
                reasoning=reasoning,
            )

        elif explanation_type == ExplanationType.CHAIN_OF_THOUGHT:
            # 5 base steps describing the consensus process
            base_steps = [
                ExplanationEvidence(
                    feature="step_1",
                    value="Task Collection",
                    importance=1.0,
                    description=f"Received task of type '{self.task.type}' with {self.consensus_strategy.value} consensus strategy",
                ),
                ExplanationEvidence(
                    feature="step_2",
                    value="Agent Execution",
                    importance=0.9,
                    description=f"Executed {self.num_agents} agents in parallel to process the task",
                ),
                ExplanationEvidence(
                    feature="step_3",
                    value="Results Collection",
                    importance=0.8,
                    description=f"Collected {self.num_agents} results with average confidence {self.avg_confidence:.2f}",
                ),
                ExplanationEvidence(
                    feature="step_4",
                    value="Consensus",
                    importance=0.7,
                    description=f"Applied {self.consensus_strategy.value} consensus strategy with agreement score {self.agreement_score:.2f}",
                ),
                ExplanationEvidence(
                    feature="step_5",
                    value="Final Decision",
                    importance=0.6,
                    description=f"Consensus output: '{self.consensus_output}' with confidence {self.consensus_confidence:.2f}",
                ),
            ]

            evidence = list(base_steps)

            if include_agent_reasoning:
                for i, r in enumerate(self.individual_results):
                    evidence.append(
                        ExplanationEvidence(
                            feature=f"agent_{r.agent_id}",
                            value=r.output,
                            importance=r.confidence,
                            description=f"Agent {r.agent_id}: predicted '{r.output}' (confidence: {r.confidence}). Reasoning: {r.explanation}",
                        )
                    )

            reasoning = (
                f"Chain-of-thought analysis of {self.consensus_strategy.value} consensus. "
                f"{self.num_agents} agents participated."
            )

            result = ExplanationResult(
                decision=decision,
                explanation_type=explanation_type,
                confidence=confidence,
                evidence=evidence,
                reasoning=reasoning,
            )

        elif explanation_type == ExplanationType.EXAMPLE_BASED:
            evidence = []
            for r in self.individual_results:
                evidence.append(
                    ExplanationEvidence(
                        feature=f"agent_{r.agent_id}",
                        value=r.output,
                        importance=r.confidence,
                        description=f"Agent {r.agent_id} produced '{r.output}' with confidence {r.confidence}",
                    )
                )
            # Sort by importance (confidence) descending
            evidence.sort(key=lambda e: e.importance, reverse=True)

            reasoning = (
                f"Example-based explanation using {self.num_agents} agent results as similar cases. "
                f"Consensus reached via {self.consensus_strategy.value}."
            )

            result = ExplanationResult(
                decision=decision,
                explanation_type=explanation_type,
                confidence=confidence,
                evidence=evidence,
                reasoning=reasoning,
            )

        elif explanation_type == ExplanationType.RULE_BASED:
            evidence = [
                ExplanationEvidence(
                    feature="consensus_rule",
                    value=self.consensus_strategy.value,
                    importance=1.0,
                    description=f"Applied {self.consensus_strategy.value} consensus strategy",
                ),
                ExplanationEvidence(
                    feature="quorum_rule",
                    value=self.num_agents,
                    importance=1.0,
                    description=f"Quorum of {self.num_agents} agents met the execution requirement",
                ),
                ExplanationEvidence(
                    feature="agreement_rule",
                    value=self.agreement_score,
                    importance=1.0,
                    description=f"Agreement score of {self.agreement_score:.2f} satisfied the consensus threshold",
                ),
            ]

            reasoning = (
                f"Rule-based consensus determination using {self.consensus_strategy.value}. "
                f"All {len(evidence)} rules evaluated with importance 1.0."
            )

            result = ExplanationResult(
                decision=decision,
                explanation_type=explanation_type,
                confidence=confidence,
                evidence=evidence,
                reasoning=reasoning,
            )

        elif explanation_type == ExplanationType.COUNTERFACTUAL:
            counterfactuals = []
            for r in self.individual_results:
                if str(r.output) != str(self.consensus_output):
                    counterfactuals.append(
                        {
                            "scenario": f"What if {r.agent_id} had higher confidence?",
                            "agent": r.agent_id,
                            "original_output": r.output,
                            "original_confidence": r.confidence,
                            "impact": "Consensus would potentially change",
                        }
                    )

            if not counterfactuals:
                # All agents agree, generate hypothetical counterfactuals
                counterfactuals.append(
                    {
                        "scenario": "What if one agent disagreed?",
                        "impact": "Agreement score would decrease, consensus may change",
                    }
                )
                counterfactuals.append(
                    {
                        "scenario": "What if confidence scores were lower?",
                        "impact": "Consensus confidence would decrease",
                    }
                )

            evidence = []
            for r in self.individual_results:
                evidence.append(
                    ExplanationEvidence(
                        feature=f"agent_{r.agent_id}",
                        value=r.output,
                        importance=r.confidence,
                        description=f"Agent {r.agent_id} contributed '{r.output}'",
                    )
                )

            reasoning = (
                "Counterfactual analysis: what if the agents had produced different results? "
                "The consensus would change if key agents altered their predictions."
            )

            result = ExplanationResult(
                decision=decision,
                explanation_type=explanation_type,
                confidence=confidence,
                evidence=evidence,
                reasoning=reasoning,
                counterfactuals=counterfactuals,
            )

        else:
            raise ValueError(f"Unsupported explanation type: {explanation_type}")

        self.explanation = result
        return result


class ConsensusEngine:
    """Static methods for computing consensus from multiple agent results."""

    @staticmethod
    def majority_vote(results: list[AgentResult]) -> tuple[Any, float, float]:
        """Compute consensus by majority vote.

        Returns:
            Tuple of (winning_output, avg_confidence_of_winners, agreement_ratio).

        Raises:
            ValueError: If results list is empty.
        """
        if not results:
            raise ValueError("Cannot compute majority vote: no results")

        # Count votes for each output
        vote_counts: Counter = Counter()
        for r in results:
            # Use string representation for hashability of complex outputs
            vote_counts[r.output] += 1

        # Find the winner (most votes; ties go to first encountered)
        max_count = max(vote_counts.values())
        winner = None
        for r in results:
            if vote_counts[r.output] == max_count:
                winner = r.output
                break

        # Calculate average confidence of agents that agree with winner
        agreeing = [r for r in results if r.output == winner]
        avg_confidence = sum(r.confidence for r in agreeing) / len(agreeing)

        # Agreement ratio
        agreement = len(agreeing) / len(results)

        return winner, avg_confidence, agreement

    @staticmethod
    def weighted_average(results: list[AgentResult]) -> tuple[Any, float, float]:
        """Compute consensus by weighted average (for numeric outputs).

        Falls back to best_confidence for non-numeric outputs.

        Returns:
            Tuple of (output, confidence, agreement_score).

        Raises:
            ValueError: If results list is empty.
        """
        if not results:
            raise ValueError("Cannot compute weighted average: no results")

        # Check if all outputs are numeric
        all_numeric = all(isinstance(r.output, (int, float)) for r in results)

        if not all_numeric:
            return ConsensusEngine.best_confidence(results)

        # Compute weighted average
        total_weight = sum(r.confidence for r in results)
        if total_weight == 0:
            # Equal weights if all confidences are zero
            weighted_output = sum(r.output for r in results) / len(results)
        else:
            weighted_output = sum(r.output * r.confidence for r in results) / total_weight

        avg_confidence = total_weight / len(results)

        # Agreement score: how close each result is to the consensus
        if len(results) == 1:
            agreement = 1.0
        else:
            max_range = max(r.output for r in results) - min(r.output for r in results)
            if max_range == 0:
                agreement = 1.0
            else:
                deviations = [abs(r.output - weighted_output) / max_range for r in results]
                agreement = 1.0 - (sum(deviations) / len(deviations))

        return weighted_output, avg_confidence, agreement

    @staticmethod
    def unanimous(results: list[AgentResult]) -> tuple[Any, float, float]:
        """Compute unanimous consensus (all agents must agree).

        Returns:
            Tuple of (output, avg_confidence, 1.0).

        Raises:
            ValueError: If results are empty or agents disagree.
        """
        if not results:
            raise ValueError("Cannot compute unanimous consensus: no results")

        first_output = results[0].output
        if not all(r.output == first_output for r in results):
            raise ValueError("Unanimous consensus failed: agents produced different outputs")

        avg_confidence = sum(r.confidence for r in results) / len(results)
        return first_output, avg_confidence, 1.0

    @staticmethod
    def best_confidence(results: list[AgentResult]) -> tuple[Any, float, float]:
        """Select the output from the agent with highest confidence.

        Returns:
            Tuple of (output, confidence, agreement_ratio).

        Raises:
            ValueError: If results list is empty.
        """
        if not results:
            raise ValueError("Cannot compute best confidence: no results")

        best = max(results, key=lambda r: r.confidence)

        # Agreement: fraction of agents that agree with the best
        agreeing = sum(1 for r in results if r.output == best.output)
        agreement = agreeing / len(results)

        return best.output, best.confidence, agreement


class AgentSwarm:
    """Coordinates multiple agents to execute tasks with consensus."""

    def __init__(self, agents: list, name: str = "swarm") -> None:
        """Initialize an agent swarm.

        Args:
            agents: List of agents. Each agent must have an agent_id attribute
                    and an async execute(task) method.
            name: Name of the swarm.

        Raises:
            ValueError: If agents list is empty.
        """
        if not agents:
            raise ValueError("AgentSwarm requires at least one agent")
        self._agents = list(agents)
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def agents(self) -> list:
        return self._agents

    @property
    def num_agents(self) -> int:
        return len(self._agents)

    def add_agent(self, agent) -> None:
        """Add an agent to the swarm."""
        self._agents.append(agent)

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the swarm by agent_id."""
        self._agents = [a for a in self._agents if a.agent_id != agent_id]

    async def execute(
        self,
        task: Task,
        generate_explanation: bool = False,
        explanation_type=None,
    ) -> SwarmResult:
        """Execute a task across all agents and compute consensus.

        Args:
            task: The task to execute.
            generate_explanation: Whether to auto-generate an explanation.
            explanation_type: The type of explanation to generate (if generate_explanation is True).

        Returns:
            SwarmResult with consensus and individual results.

        Raises:
            asyncio.TimeoutError: If execution exceeds task.timeout_seconds.
            ValueError: If require_all_agents is True and any agent fails,
                       or if all agents fail.
        """

        async def _run_agent(agent):
            return await agent.execute(task)

        async def _execute_all():
            # Run all agents in parallel
            tasks = [_run_agent(agent) for agent in self._agents]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            agent_results: list[AgentResult] = []
            failures: list[Exception] = []

            for raw in raw_results:
                if isinstance(raw, Exception):
                    failures.append(raw)
                else:
                    agent_results.append(raw)

            # Check failure conditions
            if task.require_all_agents and failures:
                raise ValueError(
                    f"Agent execution failed: {len(failures)} agent(s) failed and require_all_agents is True"
                )

            if not agent_results:
                raise ValueError("All agents failed to produce results")

            return agent_results

        # Apply timeout if specified
        if task.timeout_seconds and task.timeout_seconds > 0:
            agent_results = await asyncio.wait_for(_execute_all(), timeout=task.timeout_seconds)
        else:
            agent_results = await _execute_all()

        # Select consensus method
        strategy_map = {
            ConsensusStrategy.MAJORITY_VOTE: ConsensusEngine.majority_vote,
            ConsensusStrategy.WEIGHTED_AVERAGE: ConsensusEngine.weighted_average,
            ConsensusStrategy.UNANIMOUS: ConsensusEngine.unanimous,
            ConsensusStrategy.BEST_CONFIDENCE: ConsensusEngine.best_confidence,
        }

        consensus_fn = strategy_map[task.consensus_strategy]
        consensus_output, consensus_confidence, agreement_score = consensus_fn(agent_results)

        result = SwarmResult(
            task=task,
            consensus_output=consensus_output,
            consensus_confidence=consensus_confidence,
            individual_results=agent_results,
            consensus_strategy=task.consensus_strategy,
            agreement_score=agreement_score,
        )

        if generate_explanation:
            result.generate_explanation(
                explanation_type=explanation_type,
            )

        return result


def create_swarm(agents: list, name: str = "swarm") -> AgentSwarm:
    """Convenience function to create an AgentSwarm.

    Args:
        agents: List of agents.
        name: Name of the swarm.

    Returns:
        An AgentSwarm instance.
    """
    return AgentSwarm(agents, name=name)
