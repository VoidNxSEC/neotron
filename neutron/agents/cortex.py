"""
Cortex: Multi-Agent Orchestration & Consensus Engine

Todos os eventos de swarm/consensus são publicados como JSON estruturado em:
  neotron.cortex.consensus.v1  — resultado do swarm (via NATS)

Cada Agent tem a sua própria SynapseMemory:
  - search() antes do LLM — injeta contexto semântico histórico no prompt
  - add() após execute() — persiste resultado para execuções futuras
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from neutron.agents.synapse import SynapseMemory

# Configure logging
logger = logging.getLogger("neutron.agents.cortex")


class ConsensusStrategy(Enum):
    MAJORITY_VOTE = "majority_vote"
    UNANIMOUS = "unanimous"
    WEIGHTED_CONFIDENCE = "weighted_confidence"
    DICTATOR = "dictator"  # Primary agent decides


@dataclass
class AgentResponse:
    agent_name: str
    content: Any
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class Agent:
    """Base class for Neutron Agents with LLM integration and per-agent Synapse memory."""

    def __init__(
        self,
        name: str,
        role: str = "generalist",
        system_prompt: str | None = None,
        llm_client: Any | None = None,
        synapse: SynapseMemory | None = None,
    ):
        self.name = name
        self.role = role
        self.system_prompt = (
            system_prompt or f"You are {name}, a {role} agent in the NEXUS platform."
        )
        self._llm_client = llm_client
        # Per-agent semantic memory — provider wired lazily after LLM client is resolved
        self.synapse: SynapseMemory = synapse or SynapseMemory()

    @property
    def llm_client(self):
        """Lazy-load LLM client (mlops package or HTTP stub)."""
        if self._llm_client is None:
            try:
                from mlops.llm.client import LLMClient
            except ImportError:
                from neutron.agents._llm_http_client import LLMHTTPClient as LLMClient
            self._llm_client = LLMClient()
        return self._llm_client

    def build_prompt(self, task: dict[str, Any], memory_context: list[str] | None = None) -> str:
        """Build prompt from task, optionally injecting Synapse memory context."""
        description = task.get("description", "No description provided")
        task_type = task.get("type", "general")
        data = task.get("data", {})

        prompt = f"Task Type: {task_type}\n\n"
        prompt += f"Description: {description}\n\n"

        if data:
            prompt += f"Input Data:\n{json.dumps(data, indent=2)}\n\n"

        if memory_context:
            prompt += "Relevant context from prior experience:\n"
            for i, ctx in enumerate(memory_context, 1):
                prompt += f"  [{i}] {ctx}\n"
            prompt += "\n"

        prompt += (
            "Analyze this task and provide your response in JSON format:\n"
            '{"content": "your analysis", "confidence": 0.9, "reasoning": "brief explanation"}'
        )

        return prompt

    def parse_response(self, raw_content: str) -> tuple[str, float]:
        """Parse LLM response into content and confidence."""

        try:
            # Try to extract JSON from response
            cleaned = raw_content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            content = data.get("content", raw_content)
            confidence = float(data.get("confidence", 0.7))
            confidence = max(0.0, min(1.0, confidence))

            return content, confidence
        except (json.JSONDecodeError, ValueError):
            # Fallback to raw content
            return raw_content.strip(), 0.7

    async def execute(self, task: dict[str, Any]) -> AgentResponse:
        """Execute a task using real LLM backend, enriched with Synapse memory context."""
        description = task.get("description", "unknown")
        logger.info(f"[{self.name}] Processing task: {description}")

        # 1. Recall relevant prior experience from Synapse
        memory_context: list[str] = []
        try:
            memories = await self.synapse.search(description, limit=3)
            memory_context = [m.content for m in memories]
            if memory_context:
                logger.debug(
                    json.dumps(
                        {
                            "event": "synapse_recall",
                            "agent": self.name,
                            "recalled": len(memory_context),
                        }
                    )
                )
        except Exception as exc:
            logger.debug(f"[{self.name}] Synapse recall skipped: {exc}")

        # 2. Build prompt with memory context injected
        prompt = self.build_prompt(task, memory_context=memory_context or None)

        # 3. Call LLM
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                system=self.system_prompt,
                temperature=0.3,
                max_tokens=1024,
            )

            content, confidence = self.parse_response(response.content)

            logger.info(
                f"[{self.name}] Completed with confidence {confidence:.2f}, "
                f"tokens: {response.total_tokens}"
            )

            # 4. Persist result to Synapse for future recall
            try:
                summary = f"Task: {description} | Result: {str(content)[:200]}"
                await self.synapse.add(
                    content=summary,
                    metadata={
                        "agent": self.name,
                        "task_type": task.get("type", "general"),
                        "confidence": confidence,
                    },
                    importance=confidence,
                )
            except Exception as exc:
                logger.debug(f"[{self.name}] Synapse store skipped: {exc}")

            return AgentResponse(
                agent_name=self.name,
                content=content,
                confidence=confidence,
                metadata={
                    "role": self.role,
                    "model": response.model,
                    "tokens": response.total_tokens,
                    "finish_reason": response.finish_reason,
                    "memory_context_used": len(memory_context),
                },
            )
        except Exception as e:
            logger.error(f"[{self.name}] LLM call failed: {e}")
            return AgentResponse(
                agent_name=self.name,
                content=f"Error: {str(e)}",
                confidence=0.0,
                metadata={"role": self.role, "error": str(e)},
            )


class ConsensusEngine:
    """
    Implements voting and consensus logic for Agent Swarms.
    """

    def __init__(self, strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY_VOTE):
        self.strategy = strategy

    def reach_consensus(self, responses: list[AgentResponse]) -> dict[str, Any]:
        if not responses:
            return {"decision": None, "reason": "No responses"}

        if self.strategy == ConsensusStrategy.MAJORITY_VOTE:
            # Simple content voting
            votes = {}
            for r in responses:
                key = str(r.content)  # Simplification for voting
                votes[key] = votes.get(key, 0) + 1

            winner = max(votes, key=votes.get)
            return {
                "decision": winner,
                "confidence": votes[winner] / len(responses),
                "strategy": self.strategy.value,
            }

        elif self.strategy == ConsensusStrategy.WEIGHTED_CONFIDENCE:
            # Select response with highest confidence
            best_response = max(responses, key=lambda r: r.confidence)
            return {
                "decision": best_response.content,
                "confidence": best_response.confidence,
                "strategy": self.strategy.value,
            }

        return {"decision": responses[0].content, "reason": "Fallback"}


class AgentSwarm:
    """
    Orchestrates multiple agents to solve a task in parallel.
    """

    def __init__(
        self,
        agents: list[Agent],
        consensus_strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY_VOTE,
    ):
        self.agents = {a.name: a for a in agents}
        self.consensus_engine = ConsensusEngine(strategy=consensus_strategy)

    async def broadcast_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Send task to all agents, wait for results, compute consensus, and publish event.

        Emite `neotron.cortex.consensus.v1` via NATS (→ Owasaka / Phantom).
        """
        swarm_id = str(uuid.uuid4())
        t0 = time.monotonic()

        logger.info(
            json.dumps(
                {
                    "event": "swarm_broadcast",
                    "swarm_id": swarm_id,
                    "agents": list(self.agents.keys()),
                    "strategy": self.consensus_engine.strategy.value,
                    "task_type": task.get("type", "unknown"),
                }
            )
        )

        futures = [agent.execute(task) for agent in self.agents.values()]
        results = await asyncio.gather(*futures)

        consensus = self.consensus_engine.reach_consensus(results)
        duration_ms = (time.monotonic() - t0) * 1000

        event: dict[str, Any] = {
            "event": "cortex_consensus",
            "swarm_id": swarm_id,
            "source": "neotron",
            "subject": "neotron.cortex.consensus.v1",
            "strategy": self.consensus_engine.strategy.value,
            "agent_count": len(results),
            "duration_ms": round(duration_ms, 2),
            "consensus": consensus,
            "individual_results": [
                {
                    "agent": r.agent_name,
                    "content": r.content,
                    "confidence": r.confidence,
                    "metadata": r.metadata,
                }
                for r in results
            ],
        }

        # JSON log (Vector → Loki)
        logger.info(json.dumps(event, ensure_ascii=False, default=str))

        # NATS publish (Owasaka / Phantom)
        try:
            from neutron.compliance.events import publish  # noqa: PLC0415

            await publish("neotron.cortex.consensus.v1", event)
        except Exception as exc:  # pragma: no cover
            logger.warning("cortex: NATS publish failed: %s", exc)

        return event

    def get_agent(self, name: str) -> Agent | None:
        return self.agents.get(name)
