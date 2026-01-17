"""
SYNAPSE - Unified Memory System

The central coordinator for all memory tiers (Working, Episodic, Procedural).
Provides a unified interface for agents to recall and store information.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .working import WorkingMemory, MemoryMessage
from .episodic import EpisodicMemory, MemoryEpisode
from .procedural import ProceduralMemory, AgentSkill


@dataclass
class MemoryRecall:
    """Aggregated result of memory recall"""
    context: List[Dict[str, str]]  # From Working Memory
    episodes: List[MemoryEpisode]  # From Episodic Memory
    skills: List[AgentSkill]       # From Procedural Memory


class Synapse:
    """
    The three-tier memory system coordinator.
    """

    def __init__(
        self,
        max_working_tokens: int = 128000,
        db_url: Optional[str] = None
    ):
        self.working = WorkingMemory(max_tokens=max_working_tokens)
        self.episodic = EpisodicMemory(db_url=db_url)
        self.procedural = ProceduralMemory()

    async def remember(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Store a new message in working memory and potentially episodic memory"""
        # 1. Add to working memory (current context)
        self.working.add_message(role, content, metadata)
        
        # 2. Decide if it should be an episode (e.g., if it's a significant result)
        # For now, we store everything as a potential episode if it's from assistant or user
        if role in ["user", "assistant"] and len(content) > 10:
            await self.episodic.store(content, metadata)

    async def recall(self, query: str) -> MemoryRecall:
        """
        Perform a unified recall across all memory tiers.
        """
        # 1. Get working context
        context = self.working.get_context()
        
        # 2. Search episodic memory
        episodes = await self.episodic.search(query)
        
        # 3. Match procedural skills
        skills = self.procedural.match_skills(query)
        
        return MemoryRecall(
            context=context,
            episodes=episodes,
            skills=skills
        )

    def clear_working_memory(self):
        """Clear current context without affecting long-term memory"""
        self.working.clear()
