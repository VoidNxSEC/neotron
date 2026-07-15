"""Tests for CORTEX multi-agent orchestration."""

import pytest

from neutron.orchestration.cortex import (
    AgentResult,
    AgentSwarm,
    ConsensusEngine,
    ConsensusStrategy,
    SwarmResult,
    Task,
)

# --- Data Classes ---


class TestTask:
    def test_defaults(self):
        t = Task(type="test", input={"a": 1})
        assert t.consensus_strategy == ConsensusStrategy.MAJORITY_VOTE
        assert t.timeout_seconds == 30.0
        assert t.require_all_agents is False


class TestAgentResult:
    def test_valid(self):
        r = AgentResult(agent_id="a1", output="ok", confidence=0.9, explanation="fine")
        assert r.agent_id == "a1"
        assert r.processing_time_ms == 0.0

    def test_confidence_bounds(self):
        with pytest.raises(ValueError, match="Confidence"):
            AgentResult(agent_id="a", output="x", confidence=1.5, explanation="")
        with pytest.raises(ValueError, match="Confidence"):
            AgentResult(agent_id="a", output="x", confidence=-0.1, explanation="")

    def test_confidence_edges(self):
        AgentResult(agent_id="a", output="x", confidence=0.0, explanation="")
        AgentResult(agent_id="a", output="x", confidence=1.0, explanation="")


class TestSwarmResult:
    def _make_result(self, results):
        task = Task(type="t", input={})
        return SwarmResult(
            task=task,
            consensus_output="ok",
            consensus_confidence=0.9,
            individual_results=results,
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
            agreement_score=1.0,
        )

    def test_num_agents(self):
        results = [
            AgentResult(agent_id=f"a{i}", output="ok", confidence=0.8, explanation="")
            for i in range(3)
        ]
        sr = self._make_result(results)
        assert sr.num_agents == 3

    def test_avg_confidence(self):
        results = [
            AgentResult(agent_id="a1", output="ok", confidence=0.6, explanation=""),
            AgentResult(agent_id="a2", output="ok", confidence=0.9, explanation=""),
        ]
        sr = self._make_result(results)
        assert abs(sr.avg_confidence - 0.75) < 0.001

    def test_avg_confidence_empty(self):
        sr = self._make_result([])
        assert sr.avg_confidence == 0.0


# --- ConsensusEngine ---


class TestConsensusEngine:
    def _r(self, agent_id, output, confidence):
        return AgentResult(agent_id=agent_id, output=output, confidence=confidence, explanation="")

    # -- majority_vote --

    def test_majority_vote_clear_winner(self):
        results = [
            self._r("a1", "approve", 0.9),
            self._r("a2", "approve", 0.8),
            self._r("a3", "deny", 0.7),
        ]
        output, conf, agreement = ConsensusEngine.majority_vote(results)
        assert output == "approve"
        assert abs(conf - 0.85) < 0.001
        assert abs(agreement - 2 / 3) < 0.001

    def test_majority_vote_tie_first_wins(self):
        results = [self._r("a1", "approve", 0.9), self._r("a2", "deny", 0.8)]
        output, _, _ = ConsensusEngine.majority_vote(results)
        assert output == "approve"

    def test_majority_vote_unanimous(self):
        results = [self._r(f"a{i}", "ok", 0.9) for i in range(3)]
        output, _, agreement = ConsensusEngine.majority_vote(results)
        assert output == "ok"
        assert agreement == 1.0

    def test_majority_vote_empty(self):
        with pytest.raises(ValueError):
            ConsensusEngine.majority_vote([])

    # -- best_confidence --

    def test_best_confidence(self):
        results = [
            self._r("a1", "deny", 0.5),
            self._r("a2", "approve", 0.95),
            self._r("a3", "deny", 0.7),
        ]
        output, conf, agreement = ConsensusEngine.best_confidence(results)
        assert output == "approve"
        assert conf == 0.95
        assert abs(agreement - 1 / 3) < 0.001

    def test_best_confidence_empty(self):
        with pytest.raises(ValueError):
            ConsensusEngine.best_confidence([])

    # -- unanimous --

    def test_unanimous_agree(self):
        results = [self._r(f"a{i}", "approve", 0.8 + i * 0.05) for i in range(3)]
        output, conf, agreement = ConsensusEngine.unanimous(results)
        assert output == "approve"
        assert agreement == 1.0

    def test_unanimous_disagree(self):
        results = [self._r("a1", "approve", 0.9), self._r("a2", "deny", 0.8)]
        with pytest.raises(ValueError, match="different outputs"):
            ConsensusEngine.unanimous(results)

    def test_unanimous_empty(self):
        with pytest.raises(ValueError):
            ConsensusEngine.unanimous([])

    # -- weighted_average --

    def test_weighted_average_numeric(self):
        results = [self._r("a1", 100.0, 0.8), self._r("a2", 200.0, 0.2)]
        output, conf, _ = ConsensusEngine.weighted_average(results)
        # weighted: (100*0.8 + 200*0.2) / (0.8+0.2) = 120
        assert abs(output - 120.0) < 0.001

    def test_weighted_average_non_numeric_falls_back(self):
        results = [self._r("a1", "approve", 0.9), self._r("a2", "deny", 0.5)]
        output, conf, _ = ConsensusEngine.weighted_average(results)
        # Falls back to best_confidence
        assert output == "approve"

    def test_weighted_average_zero_weights(self):
        results = [self._r("a1", 10.0, 0.0), self._r("a2", 20.0, 0.0)]
        output, _, _ = ConsensusEngine.weighted_average(results)
        assert abs(output - 15.0) < 0.001

    def test_weighted_average_empty(self):
        with pytest.raises(ValueError):
            ConsensusEngine.weighted_average([])


# --- AgentSwarm ---


class FakeAgent:
    def __init__(self, agent_id: str, output: str = "ok", confidence: float = 0.8):
        self.agent_id = agent_id
        self._output = output
        self._confidence = confidence

    async def execute(self, task: Task) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            output=self._output,
            confidence=self._confidence,
            explanation=f"{self.agent_id} says {self._output}",
            processing_time_ms=10.0,
        )


class FailingAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    async def execute(self, task: Task) -> AgentResult:
        raise RuntimeError(f"{self.agent_id} failed")


class TestAgentSwarm:
    def test_init(self):
        agents = [FakeAgent("a1"), FakeAgent("a2")]
        swarm = AgentSwarm(agents, name="test")
        assert swarm.name == "test"
        assert swarm.num_agents == 2

    def test_init_empty(self):
        with pytest.raises(ValueError):
            AgentSwarm([])

    def test_add_remove(self):
        swarm = AgentSwarm([FakeAgent("a1")])
        swarm.add_agent(FakeAgent("a2"))
        assert swarm.num_agents == 2
        swarm.remove_agent("a1")
        assert swarm.num_agents == 1
        assert swarm.agents[0].agent_id == "a2"

    async def test_execute_majority_vote(self):
        agents = [
            FakeAgent("a1", "approve", 0.9),
            FakeAgent("a2", "approve", 0.8),
            FakeAgent("a3", "deny", 0.7),
        ]
        swarm = AgentSwarm(agents)
        task = Task(type="test", input={}, consensus_strategy=ConsensusStrategy.MAJORITY_VOTE)

        result = await swarm.execute(task)
        assert result.consensus_output == "approve"
        assert result.num_agents == 3
        assert result.agreement_score > 0.5

    async def test_execute_best_confidence(self):
        agents = [
            FakeAgent("a1", "deny", 0.5),
            FakeAgent("a2", "approve", 0.99),
        ]
        swarm = AgentSwarm(agents)
        task = Task(type="test", input={}, consensus_strategy=ConsensusStrategy.BEST_CONFIDENCE)

        result = await swarm.execute(task)
        assert result.consensus_output == "approve"
        assert result.consensus_confidence == 0.99

    async def test_execute_unanimous_success(self):
        agents = [FakeAgent(f"a{i}", "ok", 0.9) for i in range(3)]
        swarm = AgentSwarm(agents)
        task = Task(type="test", input={}, consensus_strategy=ConsensusStrategy.UNANIMOUS)

        result = await swarm.execute(task)
        assert result.consensus_output == "ok"
        assert result.agreement_score == 1.0

    async def test_execute_unanimous_failure(self):
        agents = [FakeAgent("a1", "yes", 0.9), FakeAgent("a2", "no", 0.8)]
        swarm = AgentSwarm(agents)
        task = Task(type="test", input={}, consensus_strategy=ConsensusStrategy.UNANIMOUS)

        with pytest.raises(ValueError, match="different outputs"):
            await swarm.execute(task)

    async def test_partial_failure_tolerated(self):
        agents = [FakeAgent("a1", "ok", 0.9), FailingAgent("a2")]
        swarm = AgentSwarm(agents)
        task = Task(type="test", input={}, require_all_agents=False)

        result = await swarm.execute(task)
        assert result.num_agents == 1
        assert result.consensus_output == "ok"

    async def test_require_all_agents_fails(self):
        agents = [FakeAgent("a1", "ok", 0.9), FailingAgent("a2")]
        swarm = AgentSwarm(agents)
        task = Task(type="test", input={}, require_all_agents=True)

        with pytest.raises(ValueError, match="require_all_agents"):
            await swarm.execute(task)

    async def test_all_agents_fail(self):
        agents = [FailingAgent("a1"), FailingAgent("a2")]
        swarm = AgentSwarm(agents)
        task = Task(type="test", input={})

        with pytest.raises(ValueError, match="All agents failed"):
            await swarm.execute(task)

    async def test_execute_with_explanation(self):
        agents = [FakeAgent("a1", "approve", 0.9), FakeAgent("a2", "approve", 0.8)]
        swarm = AgentSwarm(agents)
        task = Task(type="test", input={})

        result = await swarm.execute(task, generate_explanation=True)
        assert result.explanation is not None
        assert result.explanation.decision is not None
        readable = result.explanation.to_human_readable()
        assert len(readable) > 0

    async def test_timeout(self):
        import asyncio

        class SlowAgent:
            agent_id = "slow"

            async def execute(self, task):
                await asyncio.sleep(10)
                return AgentResult(agent_id="slow", output="late", confidence=0.5, explanation="")

        swarm = AgentSwarm([SlowAgent()])
        task = Task(type="test", input={}, timeout_seconds=0.1)

        with pytest.raises(asyncio.TimeoutError):
            await swarm.execute(task)
