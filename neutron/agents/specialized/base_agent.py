"""
Base class for specialized NEXUS agents.

Each agent wraps an LLM provider and produces AgentResult
compatible with CORTEX's AgentSwarm.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from neutron.agents.providers.base import LLMProvider
from neutron.orchestration.cortex import AgentResult, Task


@dataclass
class AgentConfig:
    """Configuration for a specialized agent."""

    agent_id: str
    role: str
    system_prompt: str
    temperature: float = 0.3
    max_tokens: int = 1024


class BaseSpecializedAgent:
    """Base for all specialized NEXUS agents.

    Subclasses must implement `build_prompt()` to construct the
    task-specific prompt from a Task object.
    """

    def __init__(self, config: AgentConfig, provider: LLMProvider):
        self.config = config
        self.provider = provider

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    def build_prompt(self, task: Task) -> str:
        """Build user prompt from task. Override in subclasses."""
        return json.dumps({"type": task.type, "input": task.input}, default=str)

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from text that may be wrapped in markdown fences."""
        stripped = text.strip()
        # Strip ```json ... ``` or ``` ... ```
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        return stripped

    def parse_response(self, raw_content: str) -> tuple[Any, float, str]:
        """Parse LLM response into (output, confidence, explanation).

        Tries to parse JSON with {output, confidence, explanation}.
        Handles markdown code fence wrapping.
        Falls back to raw text with default confidence.
        """
        try:
            cleaned = self._extract_json(raw_content)
            data = json.loads(cleaned)
            output = data.get("output", data.get("decision", raw_content))
            confidence = float(data.get("confidence", 0.7))
            confidence = max(0.0, min(1.0, confidence))
            explanation = data.get("explanation", data.get("reasoning", ""))
            return output, confidence, explanation
        except (json.JSONDecodeError, TypeError, ValueError):
            return raw_content.strip(), 0.5, raw_content.strip()

    async def execute(self, task: Task) -> AgentResult:
        """Execute task and return AgentResult for CORTEX."""
        start = time.monotonic()

        prompt = self.build_prompt(task)
        response = await self.provider.generate(
            prompt,
            system=self.config.system_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        output, confidence, explanation = self.parse_response(response.content)

        return AgentResult(
            agent_id=self.config.agent_id,
            output=output,
            confidence=confidence,
            explanation=explanation,
            processing_time_ms=elapsed_ms,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.config.agent_id!r}, role={self.config.role!r})"
