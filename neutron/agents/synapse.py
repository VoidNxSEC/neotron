"""
Synapse — lightweight agent-level memory with optional embedding search.

When an LLMProvider with embed() support is supplied, items are stored with
embedding vectors and search() uses cosine similarity.  Otherwise it falls
back to simple recency-based retrieval (last N items).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

try:
    from mlops.llm.providers.base import LLMProvider
except ImportError:
    from typing import Any as LLMProvider  # type: ignore


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class MemoryItem:
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0


# ---------------------------------------------------------------------------
# Math helpers (pure-python, no numpy)
# ---------------------------------------------------------------------------


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    return math.sqrt(_dot(v, v))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    denom = _norm(a) * _norm(b)
    if denom == 0.0:
        return 0.0
    return _dot(a, b) / denom


# ---------------------------------------------------------------------------
# SynapseMemory
# ---------------------------------------------------------------------------


class SynapseMemory:
    """In-memory semantic store for a single agent."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        connection_string: str | None = None,
    ) -> None:
        self.connection_string = connection_string
        self._provider = provider
        self._store: list[MemoryItem] = []
        self._embed_supported: bool | None = None  # lazy probe

    # -- internal -----------------------------------------------------------

    async def _try_embed(self, text: str) -> list[float] | None:
        """Attempt to embed *text*, returning None on failure or no provider."""
        if self._provider is None:
            return None

        # First call: probe whether the provider actually supports embed().
        if self._embed_supported is None:
            try:
                vec = await self._provider.embed(text)
                self._embed_supported = True
                return vec
            except NotImplementedError:
                self._embed_supported = False
                return None

        if not self._embed_supported:
            return None

        try:
            return await self._provider.embed(text)
        except Exception:
            return None

    # -- public API ---------------------------------------------------------

    async def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance: float = 1.0,
    ) -> MemoryItem:
        """Store a new memory item, optionally embedding it."""
        embedding = await self._try_embed(content)
        item = MemoryItem(
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            importance=importance,
        )
        self._store.append(item)
        return item

    async def search(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Return the most relevant items for *query*.

        If embeddings are available the results are ranked by cosine
        similarity (weighted by importance).  Otherwise the most recent
        *limit* items are returned.
        """
        if not self._store:
            return []

        query_vec = await self._try_embed(query)

        # Fallback: no embedding capability — return most recent.
        if query_vec is None:
            return self._store[-limit:]

        scored: list[tuple[float, MemoryItem]] = []
        for item in self._store:
            if item.embedding is None:
                continue
            sim = _cosine_similarity(query_vec, item.embedding)
            scored.append((sim * item.importance, item))

        if not scored:
            return self._store[-limit:]

        scored.sort(key=lambda t: t[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def get_recent(self, limit: int = 5, since: float | None = None) -> list[MemoryItem]:
        """Return the most recent items, optionally filtered by timestamp.

        Args:
            limit: Maximum number of items to return.
            since: If provided, only return items with timestamp >= *since*.
        """
        items = self._store
        if since is not None:
            items = [it for it in items if it.timestamp >= since]
        return items[-limit:]

    def update_importance(self, item: MemoryItem, delta: float) -> None:
        """Adjust an item's importance score by *delta* (clamped to >= 0)."""
        item.importance = max(0.0, item.importance + delta)

    async def clear(self) -> None:
        self._store = []
        self._embed_supported = None
