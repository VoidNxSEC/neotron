"""
SYNAPSE Working Memory - Sliding Window Context Management

Short-term memory for agent conversations with token-based truncation.
"""

from dataclasses import dataclass, field


@dataclass
class Message:
    role: str
    content: str
    tokens: int = 0


class WorkingMemory:
    """
    Sliding-window working memory for agent context.

    Maintains a list of messages within a token budget,
    automatically truncating oldest non-system messages
    when the budget is exceeded.
    """

    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens
        self.messages: list[Message] = []
        self.total_tokens: int = 0

    def add_message(self, role: str, content: str):
        """Add a message and truncate if over budget."""
        tokens = self._estimate_tokens(content)
        msg = Message(role=role, content=content, tokens=tokens)
        self.messages.append(msg)
        self.total_tokens += tokens

        # Truncate oldest non-system messages until within budget
        while self.total_tokens > self.max_tokens and len(self.messages) > 1:
            # Find first non-system message to remove
            for i, m in enumerate(self.messages):
                if m.role != "system":
                    self.total_tokens -= m.tokens
                    self.messages.pop(i)
                    break
            else:
                break  # Only system messages left

    def get_context(self) -> list[dict[str, str]]:
        """Return messages in standard chat format."""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def clear(self):
        """Clear all messages."""
        self.messages.clear()
        self.total_tokens = 0

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate (~4 chars per token)."""
        return max(1, len(text) // 4)
