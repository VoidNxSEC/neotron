"""
ComplianceAnalystAgent - Analyzes outputs for regulatory compliance.

Specializes in LGPD, GDPR, and EU AI Act compliance analysis.
"""

from __future__ import annotations

import json

try:
    from mlops.llm.providers.base import LLMProvider
except ImportError:
    from typing import Any as LLMProvider  # type: ignore
from neutron.orchestration.cortex import Task

from .base_agent import AgentConfig, BaseSpecializedAgent

SYSTEM_PROMPT = """You are a compliance analyst specializing in data protection regulations (LGPD, GDPR, EU AI Act).

Your job is to analyze decisions and outputs for regulatory compliance issues.

ALWAYS respond with valid JSON in this exact format:
{
  "output": "compliant" or "non_compliant" or "needs_review",
  "confidence": 0.0 to 1.0,
  "explanation": "Brief explanation of compliance status",
  "violations": ["list of specific violations found, if any"],
  "regulations": ["LGPD", "GDPR", "AI_ACT"],
  "risk_level": "low" or "medium" or "high" or "critical"
}

Be precise and cite specific articles when identifying violations."""


class ComplianceAnalystAgent(BaseSpecializedAgent):
    """Analyzes decisions for compliance with LGPD, GDPR, EU AI Act."""

    def __init__(
        self,
        provider: LLMProvider,
        agent_id: str = "compliance_analyst",
    ):
        config = AgentConfig(
            agent_id=agent_id,
            role="compliance_analyst",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=512,
        )
        super().__init__(config, provider)

    def build_prompt(self, task: Task) -> str:
        context = task.input if isinstance(task.input, str) else json.dumps(task.input, default=str)
        return (
            f"Analyze the following for regulatory compliance:\n\n"
            f"Context: {context}\n\n"
            f"Check against: LGPD, GDPR, EU AI Act.\n"
            f"Identify any violations and assess risk level."
        )
