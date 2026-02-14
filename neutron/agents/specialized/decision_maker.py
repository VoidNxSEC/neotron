"""
DecisionMakerAgent - Makes final decisions with comprehensive explanations.

Synthesizes compliance analysis and risk assessment into actionable decisions.
"""

from __future__ import annotations

import json

from neutron.agents.providers.base import LLMProvider
from neutron.orchestration.cortex import Task

from .base_agent import AgentConfig, BaseSpecializedAgent

SYSTEM_PROMPT = """You are a senior decision-maker for an AI compliance platform.

Your job is to make the final call on whether an action should proceed, synthesizing compliance and risk considerations.

ALWAYS respond with valid JSON in this exact format:
{
  "output": "approve" or "deny" or "conditional_approve",
  "confidence": 0.0 to 1.0,
  "explanation": "Clear explanation of the decision and reasoning",
  "conditions": ["list of conditions if conditional_approve"],
  "requires_human_review": true or false,
  "audit_notes": "notes for the compliance audit trail"
}

Make clear, defensible decisions. When in doubt, require human review."""


class DecisionMakerAgent(BaseSpecializedAgent):
    """Makes final decisions with comprehensive explanations."""

    def __init__(
        self,
        provider: LLMProvider,
        agent_id: str = "decision_maker",
    ):
        config = AgentConfig(
            agent_id=agent_id,
            role="decision_maker",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=512,
        )
        super().__init__(config, provider)

    def build_prompt(self, task: Task) -> str:
        context = task.input if isinstance(task.input, str) else json.dumps(task.input, default=str)
        return (
            f"Make a decision on the following:\n\n"
            f"Context: {context}\n\n"
            f"Consider compliance requirements and risk factors.\n"
            f"Decide: approve, deny, or conditional_approve."
        )
