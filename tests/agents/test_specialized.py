"""Tests for specialized NEXUS agents."""

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from neutron.agents.specialized.base_agent import AgentConfig, BaseSpecializedAgent
from neutron.agents.specialized.compliance_analyst import ComplianceAnalystAgent
from neutron.agents.specialized.decision_maker import DecisionMakerAgent
from neutron.agents.specialized.risk_assessor import RiskAssessorAgent
from neutron.orchestration.cortex import Task


@dataclass
class ProviderConfig:
    base_url: str
    model: str


@dataclass
class LLMResponse:
    content: str
    model: str
    total_tokens: int = 100
    finish_reason: str = "stop"


# --- Fixtures ---


class MockProvider:
    """Minimal mock provider with async generate."""

    def __init__(self, response_content: str = "{}"):
        self._content = response_content
        self.config = ProviderConfig(base_url="http://mock", model="mock")
        self.generate = AsyncMock(return_value=LLMResponse(content=response_content, model="mock"))

    def set_response(self, content: str):
        self._content = content
        self.generate.return_value = LLMResponse(content=content, model="mock")


@pytest.fixture
def mock_provider():
    return MockProvider()


def make_task(task_type: str = "test", input_data: dict | None = None) -> Task:
    return Task(type=task_type, input=input_data or {"key": "value"})


# --- BaseSpecializedAgent ---


class TestBaseSpecializedAgent:
    def test_agent_id(self, mock_provider):
        config = AgentConfig(agent_id="test-1", role="tester", system_prompt="test")
        agent = BaseSpecializedAgent(config, mock_provider)
        assert agent.agent_id == "test-1"

    def test_repr(self, mock_provider):
        config = AgentConfig(agent_id="a1", role="role1", system_prompt="sp")
        agent = BaseSpecializedAgent(config, mock_provider)
        r = repr(agent)
        assert "a1" in r
        assert "role1" in r

    def test_build_prompt_default(self, mock_provider):
        config = AgentConfig(agent_id="a", role="r", system_prompt="s")
        agent = BaseSpecializedAgent(config, mock_provider)
        task = make_task("loan", {"amount": 100})
        prompt = agent.build_prompt(task)
        data = json.loads(prompt)
        assert data["type"] == "loan"
        assert data["input"]["amount"] == 100

    def test_extract_json_plain(self):
        assert BaseSpecializedAgent._extract_json('{"a": 1}') == '{"a": 1}'

    def test_extract_json_markdown_fence(self):
        text = '```json\n{"a": 1}\n```'
        assert BaseSpecializedAgent._extract_json(text) == '{"a": 1}'

    def test_extract_json_bare_fence(self):
        text = '```\n{"a": 1}\n```'
        assert BaseSpecializedAgent._extract_json(text) == '{"a": 1}'

    def test_parse_response_valid_json(self, mock_provider):
        config = AgentConfig(agent_id="a", role="r", system_prompt="s")
        agent = BaseSpecializedAgent(config, mock_provider)

        raw = json.dumps(
            {
                "output": "approve",
                "confidence": 0.95,
                "explanation": "looks good",
            }
        )
        output, conf, expl = agent.parse_response(raw)
        assert output == "approve"
        assert conf == 0.95
        assert expl == "looks good"

    def test_parse_response_markdown_wrapped(self, mock_provider):
        config = AgentConfig(agent_id="a", role="r", system_prompt="s")
        agent = BaseSpecializedAgent(config, mock_provider)

        raw = '```json\n{"output": "deny", "confidence": 0.8, "explanation": "too risky"}\n```'
        output, conf, expl = agent.parse_response(raw)
        assert output == "deny"
        assert conf == 0.8

    def test_parse_response_fallback(self, mock_provider):
        config = AgentConfig(agent_id="a", role="r", system_prompt="s")
        agent = BaseSpecializedAgent(config, mock_provider)

        output, conf, expl = agent.parse_response("not json at all")
        assert output == "not json at all"
        assert conf == 0.5

    def test_parse_response_clamps_confidence(self, mock_provider):
        config = AgentConfig(agent_id="a", role="r", system_prompt="s")
        agent = BaseSpecializedAgent(config, mock_provider)

        raw = json.dumps({"output": "x", "confidence": 5.0})
        _, conf, _ = agent.parse_response(raw)
        assert conf == 1.0

        raw = json.dumps({"output": "x", "confidence": -1.0})
        _, conf, _ = agent.parse_response(raw)
        assert conf == 0.0

    def test_parse_response_decision_key(self, mock_provider):
        """Tests fallback to 'decision' key when 'output' is missing."""
        config = AgentConfig(agent_id="a", role="r", system_prompt="s")
        agent = BaseSpecializedAgent(config, mock_provider)

        raw = json.dumps({"decision": "escalate", "confidence": 0.6, "reasoning": "needs review"})
        output, conf, expl = agent.parse_response(raw)
        assert output == "escalate"
        assert expl == "needs review"

    @pytest.mark.asyncio
    async def test_execute(self, mock_provider):
        mock_provider.set_response(
            json.dumps(
                {
                    "output": "approve",
                    "confidence": 0.9,
                    "explanation": "all clear",
                }
            )
        )
        config = AgentConfig(agent_id="exec-agent", role="r", system_prompt="s")
        agent = BaseSpecializedAgent(config, mock_provider)

        result = await agent.execute(make_task("test"))
        assert result.agent_id == "exec-agent"
        assert result.output == "approve"
        assert result.confidence == 0.9
        assert result.processing_time_ms > 0


# --- ComplianceAnalystAgent ---


class TestComplianceAnalystAgent:
    def test_init_defaults(self, mock_provider):
        agent = ComplianceAnalystAgent(mock_provider)
        assert agent.agent_id == "compliance_analyst"
        assert agent.config.role == "compliance_analyst"
        assert agent.config.temperature == 0.1

    def test_build_prompt(self, mock_provider):
        agent = ComplianceAnalystAgent(mock_provider)
        task = make_task("review", {"data": "test"})
        prompt = agent.build_prompt(task)
        assert "regulatory compliance" in prompt
        assert "LGPD" in prompt
        assert "GDPR" in prompt

    @pytest.mark.asyncio
    async def test_execute_compliant(self, mock_provider):
        mock_provider.set_response(
            json.dumps(
                {
                    "output": "compliant",
                    "confidence": 0.95,
                    "explanation": "No violations found",
                    "violations": [],
                    "risk_level": "low",
                }
            )
        )
        agent = ComplianceAnalystAgent(mock_provider)
        result = await agent.execute(make_task("check"))
        assert result.output == "compliant"
        assert result.confidence == 0.95


# --- RiskAssessorAgent ---


class TestRiskAssessorAgent:
    def test_init_defaults(self, mock_provider):
        agent = RiskAssessorAgent(mock_provider)
        assert agent.agent_id == "risk_assessor"
        assert agent.config.role == "risk_assessor"
        assert agent.config.temperature == 0.2

    def test_build_prompt(self, mock_provider):
        agent = RiskAssessorAgent(mock_provider)
        task = make_task("assess", {"amount": 100000})
        prompt = agent.build_prompt(task)
        assert "risk" in prompt.lower()
        assert "100000" in prompt

    @pytest.mark.asyncio
    async def test_execute_approve(self, mock_provider):
        mock_provider.set_response(
            json.dumps(
                {
                    "output": "approve",
                    "confidence": 0.85,
                    "explanation": "Low risk profile",
                    "risk_score": 0.2,
                    "risk_factors": [],
                }
            )
        )
        agent = RiskAssessorAgent(mock_provider)
        result = await agent.execute(make_task("risk"))
        assert result.output == "approve"


# --- DecisionMakerAgent ---


class TestDecisionMakerAgent:
    def test_init_defaults(self, mock_provider):
        agent = DecisionMakerAgent(mock_provider)
        assert agent.agent_id == "decision_maker"
        assert agent.config.role == "decision_maker"
        assert agent.config.temperature == 0.2

    def test_build_prompt(self, mock_provider):
        agent = DecisionMakerAgent(mock_provider)
        task = make_task("decide", {"case": "loan"})
        prompt = agent.build_prompt(task)
        assert "decision" in prompt.lower() or "decide" in prompt.lower()

    @pytest.mark.asyncio
    async def test_execute_deny(self, mock_provider):
        mock_provider.set_response(
            json.dumps(
                {
                    "output": "deny",
                    "confidence": 0.92,
                    "explanation": "Too risky",
                    "requires_human_review": False,
                }
            )
        )
        agent = DecisionMakerAgent(mock_provider)
        result = await agent.execute(make_task("decision"))
        assert result.output == "deny"
        assert result.confidence == 0.92

    @pytest.mark.asyncio
    async def test_execute_conditional(self, mock_provider):
        mock_provider.set_response(
            json.dumps(
                {
                    "output": "conditional_approve",
                    "confidence": 0.75,
                    "explanation": "Approved with conditions",
                    "conditions": ["additional documentation required"],
                    "requires_human_review": True,
                }
            )
        )
        agent = DecisionMakerAgent(mock_provider)
        result = await agent.execute(make_task("decision"))
        assert result.output == "conditional_approve"
