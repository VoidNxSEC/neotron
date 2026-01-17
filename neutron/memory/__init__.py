"""
SYNAPSE Memory System

Provides long-term memory with semantic search via pgvector.

Components:
- MemoryStore: pgvector-based semantic memory storage
- Memory: Memory data model
- MemorySearchResult: Search result wrapper
"""

from neutron.memory.memory_store import (
    MemoryStore,
    Memory,
    MemorySearchResult,
    MemoryType,
    create_memory_store,
)

__all__ = [
    "MemoryStore",
    "Memory",
    "MemorySearchResult",
    "MemoryType",
    "create_memory_store",
]
