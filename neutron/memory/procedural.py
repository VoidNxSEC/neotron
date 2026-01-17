"""
SYNAPSE - Procedural Memory (Learned Skills & Procedures)

Procedural memory stores "how-to" knowledge, including tool 
definitions, successful prompt patterns, and specialized skills.
"""

from typing import List, Dict, Any, Optional
import pydantic


class AgentSkill(pydantic.BaseModel):
    """A learned skill or tool definition"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    examples: List[Dict[str, Any]] = pydantic.Field(default_factory=list)
    performance_score: float = 1.0


class ProceduralMemory:
    """
    Management of agent skills and standard procedures.
    """

    def __init__(self):
        self.skills: Dict[str, AgentSkill] = {}

    def register_skill(self, skill: AgentSkill):
        """Register a new skill in the procedural memory"""
        self.skills[skill.name] = skill

    def get_skill(self, name: str) -> Optional[AgentSkill]:
        """Retrieve a skill by name"""
        return self.skills.get(name)

    def match_skills(self, task_description: str) -> List[AgentSkill]:
        """
        Find relevant skills for a given task description.
        MVP: Basic keyword matching. Phase 2: Semantic matching.
        """
        relevant = []
        task_lower = task_description.lower()
        for skill in self.skills.values():
            if skill.name.lower() in task_lower or any(word in task_lower for word in skill.name.split('_')):
                relevant.append(skill)
        return relevant
