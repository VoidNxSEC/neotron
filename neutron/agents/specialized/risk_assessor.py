"""
RiskAssessorAgent - Evaluates risk levels and recommends mitigations.

Specializes in quantifying risk for financial, operational, and compliance decisions.
"""

from __future__ import annotations

import json

try:
    from mlops.llm.providers.base import LLMProvider
except ImportError:
    from typing import Any as LLMProvider  # type: ignore
from neutron.orchestration.cortex import Task

from .base_agent import AgentConfig, BaseSpecializedAgent

SYSTEM_PROMPT = """You are a risk assessment specialist for AI-driven financial and operational decisions.

Your job is to evaluate risk levels and recommend mitigations.

ALWAYS respond with valid JSON in this exact format:
{
  "output": "approve" or "deny" or "escalate",
  "confidence": 0.0 to 1.0,
  "explanation": "Brief risk assessment summary",
  "risk_score": 0.0 to 1.0,
  "risk_factors": ["list of identified risk factors"],
  "mitigations": ["list of recommended mitigations"]
}

Be quantitative when possible. Consider financial, operational, reputational, and regulatory risks."""


class RiskAssessorAgent(BaseSpecializedAgent):
    """Evaluates risk levels and recommends actions."""

    def __init__(
        self,
        provider: LLMProvider,
        agent_id: str = "risk_assessor",
    ):
        config = AgentConfig(
            agent_id=agent_id,
            role="risk_assessor",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=512,
        )
        super().__init__(config, provider)

    def build_prompt(self, task: Task) -> str:
        context = task.input if isinstance(task.input, str) else json.dumps(task.input, default=str)
        return (
            f"Assess the risk of the following decision:\n\n"
            f"Context: {context}\n\n"
            f"Evaluate financial, operational, and compliance risks.\n"
            f"Recommend: approve, deny, or escalate."
        )
