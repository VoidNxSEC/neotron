from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json

@dataclass
class MemoryItem:
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None

class SynapseMemory:
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string
        # In-memory stub for now
        self._store: List[MemoryItem] = []

    async def add(self, content: str, metadata: Dict[str, Any] = None):
        item = MemoryItem(content=content, metadata=metadata or {})
        self._store.append(item)
        # TODO: Implement actual pgvector insertion
        print(f"[Synapse] Stored: {content[:50]}...")

    async def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        # TODO: Implement cosine similarity search
        print(f"[Synapse] Searching for: {query}")
        return self._store[-limit:]

    async def clear(self):
        self._store = []
