"""
Tests for CORTEX Multi-Agent Orchestration System

Tests consensus algorithms, agent swarm coordination, and task execution.
"""

import asyncio
from typing import Any

import pytest
from neutron.orchestration.cortex import (
    AgentResult,
    AgentSwarm,
    ConsensusEngine,
    ConsensusStrategy,
    SwarmResult,
    Task,
    create_swarm,
)

from neutron.reasoning import ExplanationType

# =============================================================================
# Mock Agents
# =============================================================================


class MockAgent:
    """Mock agent for testing"""

    def __init__(self, agent_id: str, output: Any, confidence: float, delay_ms: float = 0):
        self.agent_id = agent_id
        self._output = output
        self._confidence = confidence
        self._delay_ms = delay_ms

    async def execute(self, task: Task) -> AgentResult:
        """Execute task with configured delay"""
        if self._delay_ms > 0:
            await asyncio.sleep(self._delay_ms / 1000.0)

        return AgentResult(
            agent_id=self.agent_id,
            output=self._output,
            confidence=self._confidence,
            explanation=f"Agent {self.agent_id} predicts {self._output}",
            processing_time_ms=self._delay_ms,
        )


class FailingAgent:
    """Mock agent that always fails"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    async def execute(self, task: Task) -> AgentResult:
        """Raise exception"""
        raise RuntimeError(f"Agent {self.agent_id} failed")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def classification_task():
    """Task for classification (categorical output)"""
    return Task(
        type="classification",
        input={"text": "Is this spam?"},
        consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
    )


@pytest.fixture
def regression_task():
    """Task for regression (numeric output)"""
    return Task(
        type="regression",
        input={"features": [1.0, 2.0, 3.0]},
        consensus_strategy=ConsensusStrategy.WEIGHTED_AVERAGE,
    )


# =============================================================================
# AgentResult Tests
# =============================================================================


class TestAgentResult:
    """Tests for AgentResult data model"""

    def test_valid_agent_result(self):
        """Test creating valid agent result"""
        result = AgentResult(
            agent_id="agent_1", output="spam", confidence=0.9, explanation="High spam indicators"
        )

        assert result.agent_id == "agent_1"
        assert result.output == "spam"
        assert result.confidence == 0.9
        assert result.explanation == "High spam indicators"

    def test_confidence_validation(self):
        """Test confidence score validation"""
        # Valid confidences
        AgentResult(agent_id="a", output="x", confidence=0.0, explanation="")
        AgentResult(agent_id="a", output="x", confidence=1.0, explanation="")
        AgentResult(agent_id="a", output="x", confidence=0.5, explanation="")

        # Invalid confidences
        with pytest.raises(ValueError):
            AgentResult(agent_id="a", output="x", confidence=-0.1, explanation="")

        with pytest.raises(ValueError):
            AgentResult(agent_id="a", output="x", confidence=1.1, explanation="")


# =============================================================================
# Consensus Engine Tests
# =============================================================================


class TestConsensusEngine:
    """Tests for consensus algorithms"""

    def test_majority_vote_clear_winner(self):
        """Test majority vote with clear winner"""
        results = [
            AgentResult("a1", "spam", 0.9, ""),
            AgentResult("a2", "spam", 0.8, ""),
            AgentResult("a3", "ham", 0.7, ""),
        ]

        output, confidence, agreement = ConsensusEngine.majority_vote(results)

        assert output == "spam"
        assert 0.8 <= confidence <= 0.9  # Average of agreeing agents
        assert agreement == 2 / 3  # 2 out of 3 agree

    def test_majority_vote_tie(self):
        """Test majority vote with tie (first wins)"""
        results = [
            AgentResult("a1", "spam", 0.9, ""),
            AgentResult("a2", "ham", 0.8, ""),
        ]

        output, confidence, agreement = ConsensusEngine.majority_vote(results)

        assert output in ["spam", "ham"]  # Either could win
        assert agreement == 0.5  # 50% agreement

    def test_weighted_average_numeric(self):
        """Test weighted average with numeric outputs"""
        results = [
            AgentResult("a1", 10.0, 0.9, ""),  # High confidence
            AgentResult("a2", 5.0, 0.3, ""),  # Low confidence
            AgentResult("a3", 8.0, 0.6, ""),  # Medium confidence
        ]

        output, confidence, agreement = ConsensusEngine.weighted_average(results)

        # Should be closer to 10.0 due to high confidence
        assert 8.0 < output < 10.0
        assert confidence > 0.0

    def test_weighted_average_non_numeric_fallback(self):
        """Test weighted average falls back to best_confidence for non-numeric"""
        results = [
            AgentResult("a1", "spam", 0.9, ""),
            AgentResult("a2", "ham", 0.3, ""),
        ]

        output, confidence, agreement = ConsensusEngine.weighted_average(results)

        assert output == "spam"  # Highest confidence
        assert confidence == 0.9

    def test_unanimous_agreement(self):
        """Test unanimous consensus with agreement"""
        results = [
            AgentResult("a1", "spam", 0.9, ""),
            AgentResult("a2", "spam", 0.8, ""),
            AgentResult("a3", "spam", 0.7, ""),
        ]

        output, confidence, agreement = ConsensusEngine.unanimous(results)

        assert output == "spam"
        assert confidence == pytest.approx(0.8, rel=0.1)  # Average
        assert agreement == 1.0  # Perfect agreement

    def test_unanimous_disagreement(self):
        """Test unanimous consensus fails with disagreement"""
        results = [
            AgentResult("a1", "spam", 0.9, ""),
            AgentResult("a2", "ham", 0.8, ""),
        ]

        with pytest.raises(ValueError, match="Unanimous consensus failed"):
            ConsensusEngine.unanimous(results)

    def test_best_confidence(self):
        """Test best confidence strategy"""
        results = [
            AgentResult("a1", "spam", 0.7, ""),
            AgentResult("a2", "ham", 0.95, ""),  # Highest confidence
            AgentResult("a3", "spam", 0.6, ""),
        ]

        output, confidence, agreement = ConsensusEngine.best_confidence(results)

        assert output == "ham"
        assert confidence == 0.95
        assert agreement == 1 / 3  # Only 1 agent agrees with best

    def test_empty_results_error(self):
        """Test that empty results raise error"""
        with pytest.raises(ValueError, match="no results"):
            ConsensusEngine.majority_vote([])

        with pytest.raises(ValueError, match="no results"):
            ConsensusEngine.weighted_average([])


# =============================================================================
# AgentSwarm Tests
# =============================================================================


class TestAgentSwarm:
    """Tests for agent swarm coordination"""

    @pytest.mark.asyncio
    async def test_create_swarm(self):
        """Test creating agent swarm"""
        agents = [
            MockAgent("a1", "spam", 0.9),
            MockAgent("a2", "spam", 0.8),
        ]

        swarm = AgentSwarm(agents, name="test_swarm")

        assert swarm.name == "test_swarm"
        assert swarm.num_agents == 2

    @pytest.mark.asyncio
    async def test_execute_majority_vote(self, classification_task):
        """Test swarm execution with majority vote"""
        agents = [
            MockAgent("a1", "spam", 0.9),
            MockAgent("a2", "spam", 0.8),
            MockAgent("a3", "ham", 0.7),
        ]

        swarm = AgentSwarm(agents)
        result = await swarm.execute(classification_task)

        assert isinstance(result, SwarmResult)
        assert result.consensus_output == "spam"
        assert result.num_agents == 3
        assert len(result.individual_results) == 3
        assert result.agreement_score == pytest.approx(2 / 3, rel=0.1)

    @pytest.mark.asyncio
    async def test_execute_weighted_average(self, regression_task):
        """Test swarm execution with weighted average"""
        agents = [
            MockAgent("a1", 10.0, 0.9),
            MockAgent("a2", 5.0, 0.3),
            MockAgent("a3", 8.0, 0.6),
        ]

        swarm = AgentSwarm(agents)
        result = await swarm.execute(regression_task)

        assert isinstance(result, SwarmResult)
        # Should be weighted toward 10.0 (higher confidence)
        assert 8.0 < result.consensus_output < 10.0
        assert result.num_agents == 3

    @pytest.mark.asyncio
    async def test_execute_unanimous(self):
        """Test swarm execution with unanimous consensus"""
        agents = [
            MockAgent("a1", "spam", 0.9),
            MockAgent("a2", "spam", 0.8),
        ]

        task = Task(
            type="classification",
            input={"text": "spam?"},
            consensus_strategy=ConsensusStrategy.UNANIMOUS,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)

        assert result.consensus_output == "spam"
        assert result.agreement_score == 1.0

    @pytest.mark.asyncio
    async def test_execute_unanimous_fails(self):
        """Test unanimous consensus fails with disagreement"""
        agents = [
            MockAgent("a1", "spam", 0.9),
            MockAgent("a2", "ham", 0.8),
        ]

        task = Task(
            type="classification",
            input={"text": "spam?"},
            consensus_strategy=ConsensusStrategy.UNANIMOUS,
        )

        swarm = AgentSwarm(agents)

        with pytest.raises(ValueError, match="Unanimous consensus failed"):
            await swarm.execute(task)

    @pytest.mark.asyncio
    async def test_execute_best_confidence(self):
        """Test swarm execution with best confidence strategy"""
        agents = [
            MockAgent("a1", "spam", 0.7),
            MockAgent("a2", "ham", 0.95),
            MockAgent("a3", "spam", 0.6),
        ]

        task = Task(
            type="classification",
            input={"text": "spam?"},
            consensus_strategy=ConsensusStrategy.BEST_CONFIDENCE,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)

        assert result.consensus_output == "ham"
        assert result.consensus_confidence == 0.95

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test that agents execute in parallel"""
        # Each agent has 100ms delay
        agents = [
            MockAgent("a1", "spam", 0.9, delay_ms=100),
            MockAgent("a2", "spam", 0.8, delay_ms=100),
            MockAgent("a3", "spam", 0.7, delay_ms=100),
        ]

        task = Task(
            type="classification",
            input={"text": "spam?"},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
            timeout_seconds=1.0,
        )

        swarm = AgentSwarm(agents)

        start_time = asyncio.get_event_loop().time()
        result = await swarm.execute(task)
        elapsed_time = asyncio.get_event_loop().time() - start_time

        # Should take ~100ms (parallel), not ~300ms (sequential)
        assert elapsed_time < 0.2  # 200ms max (with overhead)
        assert result.num_agents == 3

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test timeout when agents take too long"""
        # Agents with 2 second delay, but task has 0.5s timeout
        agents = [
            MockAgent("a1", "spam", 0.9, delay_ms=2000),
        ]

        task = Task(type="classification", input={"text": "spam?"}, timeout_seconds=0.5)

        swarm = AgentSwarm(agents)

        with pytest.raises(asyncio.TimeoutError):
            await swarm.execute(task)

    @pytest.mark.asyncio
    async def test_partial_failure_allowed(self):
        """Test that partial agent failures are allowed by default"""
        agents = [
            MockAgent("a1", "spam", 0.9),
            FailingAgent("a2"),  # This agent will fail
            MockAgent("a3", "spam", 0.7),
        ]

        task = Task(
            type="classification", input={"text": "spam?"}, require_all_agents=False  # Default
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)

        # Should succeed with 2 agents
        assert result.num_agents == 2
        assert result.consensus_output == "spam"

    @pytest.mark.asyncio
    async def test_partial_failure_not_allowed(self):
        """Test that partial failures raise error when required"""
        agents = [
            MockAgent("a1", "spam", 0.9),
            FailingAgent("a2"),  # This agent will fail
            MockAgent("a3", "spam", 0.7),
        ]

        task = Task(
            type="classification", input={"text": "spam?"}, require_all_agents=True  # Require all
        )

        swarm = AgentSwarm(agents)

        with pytest.raises(ValueError, match="failed"):
            await swarm.execute(task)

    @pytest.mark.asyncio
    async def test_all_agents_fail(self):
        """Test error when all agents fail"""
        agents = [
            FailingAgent("a1"),
            FailingAgent("a2"),
        ]

        task = Task(type="classification", input={"text": "spam?"})

        swarm = AgentSwarm(agents)

        with pytest.raises(ValueError, match="All agents failed"):
            await swarm.execute(task)

    def test_add_agent(self):
        """Test adding agent to swarm"""
        swarm = AgentSwarm([MockAgent("a1", "spam", 0.9)])
        assert swarm.num_agents == 1

        swarm.add_agent(MockAgent("a2", "ham", 0.8))
        assert swarm.num_agents == 2

    def test_remove_agent(self):
        """Test removing agent from swarm"""
        swarm = AgentSwarm(
            [
                MockAgent("a1", "spam", 0.9),
                MockAgent("a2", "ham", 0.8),
            ]
        )
        assert swarm.num_agents == 2

        swarm.remove_agent("a1")
        assert swarm.num_agents == 1
        assert swarm.agents[0].agent_id == "a2"

    def test_empty_swarm_error(self):
        """Test that empty swarm raises error"""
        with pytest.raises(ValueError, match="at least one agent"):
            AgentSwarm([])


# =============================================================================
# SwarmResult Tests
# =============================================================================


class TestSwarmResult:
    """Tests for SwarmResult data model"""

    def test_swarm_result_properties(self):
        """Test SwarmResult computed properties"""
        results = [
            AgentResult("a1", "spam", 0.9, ""),
            AgentResult("a2", "spam", 0.8, ""),
            AgentResult("a3", "ham", 0.7, ""),
        ]

        swarm_result = SwarmResult(
            task=Task(type="test", input={}),
            consensus_output="spam",
            consensus_confidence=0.85,
            individual_results=results,
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
            agreement_score=2 / 3,
        )

        assert swarm_result.num_agents == 3
        assert swarm_result.avg_confidence == pytest.approx(0.8, rel=0.1)


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestUtilityFunctions:
    """Tests for utility functions"""

    @pytest.mark.asyncio
    async def test_create_swarm(self):
        """Test create_swarm convenience function"""
        agents = [
            MockAgent("a1", "spam", 0.9),
            MockAgent("a2", "ham", 0.8),
        ]

        swarm = create_swarm(agents, name="test")

        assert isinstance(swarm, AgentSwarm)
        assert swarm.name == "test"
        assert swarm.num_agents == 2


# =============================================================================
# Integration Tests
# =============================================================================


class TestCortexIntegration:
    """Integration tests for real-world scenarios"""

    @pytest.mark.asyncio
    async def test_ensemble_classification(self):
        """Test ensemble of classifiers with majority vote"""
        # Simulate 5 spam classifiers
        agents = [
            MockAgent("naive_bayes", "spam", 0.85),
            MockAgent("svm", "spam", 0.92),
            MockAgent("random_forest", "spam", 0.88),
            MockAgent("neural_net", "ham", 0.75),
            MockAgent("logistic_reg", "spam", 0.80),
        ]

        task = Task(
            type="spam_classification",
            input={"email": "Buy now! Limited offer!"},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
        )

        swarm = AgentSwarm(agents, name="spam_ensemble")
        result = await swarm.execute(task)

        # 4 out of 5 say spam
        assert result.consensus_output == "spam"
        assert result.agreement_score == 0.8
        assert result.num_agents == 5

    @pytest.mark.asyncio
    async def test_regression_ensemble(self):
        """Test ensemble of regressors with weighted average"""
        # Simulate price prediction models
        agents = [
            MockAgent("linear_reg", 50000.0, 0.6),
            MockAgent("gradient_boost", 52000.0, 0.9),  # Most confident
            MockAgent("neural_net", 48000.0, 0.7),
        ]

        task = Task(
            type="price_prediction",
            input={"features": {"sqft": 2000, "bedrooms": 3}},
            consensus_strategy=ConsensusStrategy.WEIGHTED_AVERAGE,
        )

        swarm = AgentSwarm(agents, name="price_ensemble")
        result = await swarm.execute(task)

        # Should be weighted toward 52000 (highest confidence)
        assert 50000 < result.consensus_output < 52000
        assert result.num_agents == 3

    @pytest.mark.asyncio
    async def test_critical_decision_unanimous(self):
        """Test critical decision requiring unanimous agreement"""
        # Medical diagnosis - all models must agree
        agents = [
            MockAgent("model_a", "benign", 0.9),
            MockAgent("model_b", "benign", 0.85),
            MockAgent("model_c", "benign", 0.88),
        ]

        task = Task(
            type="medical_diagnosis",
            input={"scan": "data"},
            consensus_strategy=ConsensusStrategy.UNANIMOUS,
            require_all_agents=True,
        )

        swarm = AgentSwarm(agents, name="diagnosis_ensemble")
        result = await swarm.execute(task)

        assert result.consensus_output == "benign"
        assert result.agreement_score == 1.0  # Unanimous

    @pytest.mark.asyncio
    async def test_best_expert_selection(self):
        """Test selecting best expert based on confidence"""
        # Different specialized models
        agents = [
            MockAgent("generalist", "medium_risk", 0.6),
            MockAgent("specialist", "high_risk", 0.95),  # Expert on this case
            MockAgent("baseline", "low_risk", 0.5),
        ]

        task = Task(
            type="risk_assessment",
            input={"case": "complex"},
            consensus_strategy=ConsensusStrategy.BEST_CONFIDENCE,
        )

        swarm = AgentSwarm(agents, name="risk_ensemble")
        result = await swarm.execute(task)

        # Trust the most confident expert
        assert result.consensus_output == "high_risk"
        assert result.consensus_confidence == 0.95


# =============================================================================
# ORACLE Integration Tests
# =============================================================================


class TestOracleIntegration:
    """Tests for ORACLE explainability integration with CORTEX"""

    @pytest.mark.asyncio
    async def test_generate_explanation_feature_importance(self):
        """Test generating feature importance explanation for consensus"""
        agents = [
            MockAgent("agent_a", "approved", 0.9),
            MockAgent("agent_b", "approved", 0.85),
            MockAgent("agent_c", "denied", 0.6),
        ]

        task = Task(
            type="loan_decision",
            input={"credit_score": 750, "income": 80000},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)

        # Generate explanation
        explanation = result.generate_explanation(
            explanation_type=ExplanationType.FEATURE_IMPORTANCE
        )

        assert explanation is not None
        assert explanation.decision == "Swarm consensus: approved"
        assert explanation.explanation_type == ExplanationType.FEATURE_IMPORTANCE
        assert explanation.confidence == result.consensus_confidence
        assert len(explanation.evidence) > 0

        # Check that explanation is stored in result
        assert result.explanation is not None
        assert result.explanation == explanation

    @pytest.mark.asyncio
    async def test_generate_explanation_chain_of_thought(self):
        """Test generating chain-of-thought explanation"""
        agents = [
            MockAgent("classifier_a", "spam", 0.95),
            MockAgent("classifier_b", "spam", 0.9),
        ]

        task = Task(
            type="spam_detection",
            input={"email": "test"},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)

        explanation = result.generate_explanation(explanation_type=ExplanationType.CHAIN_OF_THOUGHT)

        assert explanation.explanation_type == ExplanationType.CHAIN_OF_THOUGHT

        # Should have reasoning steps
        assert len(explanation.evidence) >= 5  # At least 5 steps

        # Verify step structure
        step_features = [e.feature for e in explanation.evidence]
        assert "step_1" in step_features
        assert "step_2" in step_features

    @pytest.mark.asyncio
    async def test_generate_explanation_example_based(self):
        """Test generating example-based explanation with agent results"""
        agents = [
            MockAgent("expert_1", "high_risk", 0.92),
            MockAgent("expert_2", "high_risk", 0.88),
            MockAgent("expert_3", "medium_risk", 0.75),
        ]

        task = Task(
            type="risk_assessment",
            input={"transaction": "large_transfer"},
            consensus_strategy=ConsensusStrategy.BEST_CONFIDENCE,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)

        explanation = result.generate_explanation(explanation_type=ExplanationType.EXAMPLE_BASED)

        assert explanation.explanation_type == ExplanationType.EXAMPLE_BASED

        # Should use individual agent results as "similar cases"
        assert len(explanation.evidence) == 3  # 3 agents = 3 similar cases

        # Evidence should be sorted by importance (confidence)
        importances = [e.importance for e in explanation.evidence]
        assert importances == sorted(importances, reverse=True)

    @pytest.mark.asyncio
    async def test_generate_explanation_rule_based(self):
        """Test generating rule-based explanation"""
        agents = [
            MockAgent("rule_engine_1", "allow", 0.99),
            MockAgent("rule_engine_2", "allow", 1.0),
        ]

        task = Task(
            type="access_control",
            input={"user": "admin"},
            consensus_strategy=ConsensusStrategy.UNANIMOUS,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)

        explanation = result.generate_explanation(explanation_type=ExplanationType.RULE_BASED)

        assert explanation.explanation_type == ExplanationType.RULE_BASED

        # Should have rules in evidence
        assert len(explanation.evidence) >= 3  # At least 3 consensus rules

        # All rules should have importance 1.0 (deterministic)
        for evidence in explanation.evidence:
            assert evidence.importance == 1.0

    @pytest.mark.asyncio
    async def test_generate_explanation_counterfactual(self):
        """Test generating counterfactual explanation"""
        agents = [
            MockAgent("agent_1", "approved", 0.85),
            MockAgent("agent_2", "approved", 0.8),
        ]

        task = Task(
            type="decision",
            input={"score": 750},
            consensus_strategy=ConsensusStrategy.WEIGHTED_AVERAGE,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)

        explanation = result.generate_explanation(explanation_type=ExplanationType.COUNTERFACTUAL)

        assert explanation.explanation_type == ExplanationType.COUNTERFACTUAL

        # Should have counterfactuals
        assert len(explanation.counterfactuals) > 0

        # Reasoning should mention "what if"
        assert (
            "what if" in explanation.reasoning.lower() or "would" in explanation.reasoning.lower()
        )

    @pytest.mark.asyncio
    async def test_auto_generate_explanation_on_execute(self):
        """Test auto-generating explanation during execute()"""
        agents = [
            MockAgent("agent_a", "positive", 0.9),
            MockAgent("agent_b", "positive", 0.85),
        ]

        task = Task(
            type="sentiment_analysis",
            input={"text": "Great product!"},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
        )

        swarm = AgentSwarm(agents)

        # Execute with auto-explanation
        result = await swarm.execute(
            task, generate_explanation=True, explanation_type=ExplanationType.FEATURE_IMPORTANCE
        )

        # Explanation should be automatically generated
        assert result.explanation is not None
        assert result.explanation.explanation_type == ExplanationType.FEATURE_IMPORTANCE
        assert result.explanation.confidence == result.consensus_confidence

    @pytest.mark.asyncio
    async def test_auto_generate_explanation_chain_of_thought(self):
        """Test auto-generating chain-of-thought explanation"""
        agents = [
            MockAgent("analyzer_1", "fraudulent", 0.95),
            MockAgent("analyzer_2", "fraudulent", 0.92),
            MockAgent("analyzer_3", "legitimate", 0.6),
        ]

        task = Task(
            type="fraud_detection",
            input={"transaction": "suspicious"},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(
            task, generate_explanation=True, explanation_type=ExplanationType.CHAIN_OF_THOUGHT
        )

        # Should have chain-of-thought explanation
        assert result.explanation is not None
        assert result.explanation.explanation_type == ExplanationType.CHAIN_OF_THOUGHT

        # Should include agent reasoning in steps
        evidence_descriptions = " ".join([e.description for e in result.explanation.evidence])
        assert "analyzer_1" in evidence_descriptions or "analyzer" in evidence_descriptions

    @pytest.mark.asyncio
    async def test_explanation_includes_agent_metadata(self):
        """Test that explanation includes individual agent results"""
        agents = [
            MockAgent("agent_1", "class_a", 0.8),
            MockAgent("agent_2", "class_b", 0.75),
        ]

        task = Task(
            type="classification",
            input={"data": "test"},
            consensus_strategy=ConsensusStrategy.BEST_CONFIDENCE,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)
        explanation = result.generate_explanation()

        # Check that input_data includes task metadata
        human_readable = explanation.to_human_readable()
        assert "classification" in human_readable or "task" in human_readable.lower()

    @pytest.mark.asyncio
    async def test_explanation_without_auto_generate(self):
        """Test that explanation is None without auto-generate"""
        agents = [MockAgent("agent_1", "result", 0.9)]

        task = Task(type="task", input={}, consensus_strategy=ConsensusStrategy.MAJORITY_VOTE)

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task, generate_explanation=False)

        # Explanation should not be auto-generated
        assert result.explanation is None

        # But can still generate manually
        explanation = result.generate_explanation()
        assert explanation is not None

    @pytest.mark.asyncio
    async def test_explanation_to_multiple_formats(self):
        """Test converting explanation to different formats"""
        agents = [
            MockAgent("agent_1", "approved", 0.9),
            MockAgent("agent_2", "approved", 0.85),
        ]

        task = Task(
            type="approval",
            input={"request": "test"},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)
        explanation = result.generate_explanation(
            explanation_type=ExplanationType.FEATURE_IMPORTANCE
        )

        # Test all output formats
        human_readable = explanation.to_human_readable()
        json_output = explanation.to_json()
        markdown = explanation.to_markdown()

        assert "approved" in human_readable
        assert "approved" in json_output
        assert "approved" in markdown

        # JSON should be valid
        import json

        parsed = json.loads(json_output)
        assert parsed["decision"] == "Swarm consensus: approved"

    @pytest.mark.asyncio
    async def test_explanation_with_include_agent_reasoning(self):
        """Test controlling agent reasoning inclusion in explanations"""
        agents = [
            MockAgent("agent_a", "yes", 0.9),
            MockAgent("agent_b", "yes", 0.85),
        ]

        task = Task(
            type="binary_decision", input={}, consensus_strategy=ConsensusStrategy.MAJORITY_VOTE
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)

        # With agent reasoning
        explanation_with = result.generate_explanation(
            explanation_type=ExplanationType.CHAIN_OF_THOUGHT, include_agent_reasoning=True
        )

        # Should include agent details in evidence

        assert len(explanation_with.evidence) > 5  # 5 base steps + agent details

        # Without agent reasoning
        explanation_without = result.generate_explanation(
            explanation_type=ExplanationType.CHAIN_OF_THOUGHT, include_agent_reasoning=False
        )

        # Should only have base reasoning steps
        assert len(explanation_without.evidence) == 5  # Only 5 base steps

    @pytest.mark.asyncio
    async def test_explanation_confidence_matches_consensus(self):
        """Test that explanation confidence matches consensus confidence"""
        agents = [
            MockAgent("agent_1", 0.8, 0.9),  # output=0.8, confidence=0.9
            MockAgent("agent_2", 0.75, 0.85),
        ]

        task = Task(
            type="prediction", input={}, consensus_strategy=ConsensusStrategy.WEIGHTED_AVERAGE
        )

        swarm = AgentSwarm(agents)
        result = await swarm.execute(task)
        explanation = result.generate_explanation()

        # Explanation confidence should match consensus confidence
        assert explanation.confidence == result.consensus_confidence
