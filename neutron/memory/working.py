"""
SYNAPSE - Working Memory (Short-term Context)

Working memory represents the current "attention" of the agent, 
limited by the context window of the LLM. It is ephemeral and 
stored in-memory during a session.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pydantic


class MemoryMessage(pydantic.BaseModel):
    """A single message in the working memory"""
    role: str  # system, user, assistant, tool
    content: str
    timestamp: datetime = pydantic.Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = pydantic.Field(default_factory=dict)
    tokens: Optional[int] = None


class WorkingMemory:
    """
    Ephemeral in-memory context management.
    Handles token counting (estimated) and sliding window for context.
    """

    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self.messages: List[MemoryMessage] = []
        self._current_tokens: int = 0

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a new message to the context"""
        # Rough token estimation: ~4 chars per token if not provided
        estimated_tokens = len(content) // 4 
        
        message = MemoryMessage(
            role=role,
            content=content,
            metadata=metadata or {},
            tokens=estimated_tokens
        )
        
        self.messages.append(message)
        self._current_tokens += estimated_tokens
        
        # Enforce sliding window if limit exceeded
        self._truncate_if_needed()

    def _truncate_if_needed(self):
        """Removes oldest messages until token limit is met"""
        while self._current_tokens > self.max_tokens and len(self.messages) > 1:
            # We keep the system message if it's the first one
            idx_to_remove = 0
            if self.messages[0].role == "system" and len(self.messages) > 1:
                idx_to_remove = 1
            
            removed = self.messages.pop(idx_to_remove)
            if removed.tokens:
                self._current_tokens -= removed.tokens

    def get_context(self) -> List[Dict[str, str]]:
        """Return messages in OpenAI/Claude format"""
        return [
            {"role": m.role, "content": m.content} 
            for m in self.messages
        ]

    def clear(self):
        """Clear all messages"""
        self.messages = []
        self._current_tokens = 0

    @property
    def total_tokens(self) -> int:
        return self._current_tokens
