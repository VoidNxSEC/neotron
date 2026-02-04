"""
Cortex: Multi-Agent Orchestration & Consensus Engine
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import random

# Configure logging
logger = logging.getLogger("neutron.agents.cortex")

class ConsensusStrategy(Enum):
    MAJORITY_VOTE = "majority_vote"
    UNANIMOUS = "unanimous"
    WEIGHTED_CONFIDENCE = "weighted_confidence"
    DICTATOR = "dictator" # Primary agent decides

@dataclass
class AgentResponse:
    agent_name: str
    content: Any
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class Agent:
    """Base class for Neutron Agents"""
    def __init__(self, name: str, role: str = "generalist"):
        self.name = name
        self.role = role
    
    async def execute(self, task: Dict[str, Any]) -> AgentResponse:
        """
        Execute a task. In a real scenario, this delegates to LLM/Tool.
        For infrastructure plumbing, we simulate processing.
        """
        # TODO: Connect to Reactor/LLM backend here
        logger.info(f"[{self.name}] Processing task: {task.get('description', 'unknown')}")
        
        # Simulate work
        await asyncio.sleep(0.1) 
        
        return AgentResponse(
            agent_name=self.name,
            content=f"Processed by {self.name}",
            confidence=0.9,
            metadata={"role": self.role}
        )

class ConsensusEngine:
    """
    Implements voting and consensus logic for Agent Swarms.
    """
    def __init__(self, strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY_VOTE):
        self.strategy = strategy

    def reach_consensus(self, responses: List[AgentResponse]) -> Dict[str, Any]:
        if not responses:
            return {"decision": None, "reason": "No responses"}

        if self.strategy == ConsensusStrategy.MAJORITY_VOTE:
            # Simple content voting
            votes = {}
            for r in responses:
                key = str(r.content) # Simplification for voting
                votes[key] = votes.get(key, 0) + 1
            
            winner = max(votes, key=votes.get)
            return {
                "decision": winner,
                "confidence": votes[winner] / len(responses),
                "strategy": self.strategy.value
            }
            
        elif self.strategy == ConsensusStrategy.WEIGHTED_CONFIDENCE:
            # Select response with highest confidence
            best_response = max(responses, key=lambda r: r.confidence)
            return {
                "decision": best_response.content,
                "confidence": best_response.confidence,
                "strategy": self.strategy.value
            }

        return {"decision": responses[0].content, "reason": "Fallback"}

class AgentSwarm:
    """
    Orchestrates multiple agents to solve a task in parallel.
    """
    def __init__(self, agents: List[Agent], consensus_strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY_VOTE):
        self.agents = {a.name: a for a in agents}
        self.consensus_engine = ConsensusEngine(strategy=consensus_strategy)

    async def broadcast_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send task to all agents, wait for results, and compute consensus.
        """
        logger.info(f"Broadcasting task to {len(self.agents)} agents")
        
        futures = [agent.execute(task) for agent in self.agents.values()]
        results = await asyncio.gather(*futures)
        
        consensus = self.consensus_engine.reach_consensus(results)
        
        return {
            "individual_results": [
                {"agent": r.agent_name, "content": r.content, "confidence": r.confidence}
                for r in results
            ],
            "consensus": consensus
        }

    def get_agent(self, name: str) -> Optional[Agent]:
        return self.agents.get(name)
