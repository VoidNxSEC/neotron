"""
SYNAPSE Memory Store - PostgreSQL + pgvector Semantic Memory

Production memory store with GDPR-compliant deletion and semantic search.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

try:
    import numpy as np
except ImportError:
    np = None

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None


@dataclass
class Memory:
    """A single memory entry."""

    id: int | None
    agent_id: str
    content: str
    embedding: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    importance_score: float = 0.5
    memory_type: str = "episodic"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not 0.0 <= self.importance_score <= 1.0:
            raise ValueError(
                f"Importance score must be between 0.0 and 1.0, got {self.importance_score}"
            )


@dataclass
class MemorySearchResult:
    """Result of a memory search with similarity score."""

    memory: Memory
    similarity: float
    rank: int


class MemoryStore:
    """PostgreSQL + pgvector memory store with GDPR support."""

    def __init__(self, connection_string: str | None = None):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL", "postgresql://neutron:neutron@localhost:5432/temporal"
        )
        self._conn = None

    def _get_connection(self):
        if self._conn is None and psycopg2 is not None:
            self._conn = psycopg2.connect(
                self.connection_string, cursor_factory=psycopg2.extras.RealDictCursor
            )
        return self._conn

    def store(
        self,
        agent_id: str,
        content: str,
        embedding: Any = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float = 0.5,
        tags: list[str] | None = None,
        memory_type: str = "episodic",
    ) -> int:
        """Store a memory and return its ID."""
        if not 0.0 <= importance_score <= 1.0:
            raise ValueError(f"Importance score must be 0.0-1.0, got {importance_score}")

        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO synapse_memories
                   (agent_id, content, embedding, metadata, importance_score, memory_type, tags)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    agent_id,
                    content,
                    embedding.tolist() if hasattr(embedding, "tolist") else embedding,
                    psycopg2.extras.Json(metadata or {}),
                    importance_score,
                    memory_type,
                    tags or [],
                ),
            )
            memory_id = cur.fetchone()[0]
            conn.commit()
            return memory_id

    def search(
        self,
        query_embedding: Any,
        agent_id: str | None = None,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
    ) -> list[MemorySearchResult]:
        """Search memories by semantic similarity."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT *, 1 - (embedding <=> %s::vector) as similarity
                   FROM synapse_memories
                   WHERE deleted_at IS NULL
                   AND (%s IS NULL OR agent_id = %s)
                   ORDER BY embedding <=> %s::vector
                   LIMIT %s""",
                (query_embedding.tolist(), agent_id, agent_id, query_embedding.tolist(), top_k),
            )
            rows = cur.fetchall()

        results = []
        for rank, row in enumerate(rows, 1):
            memory = Memory(
                id=row["id"],
                agent_id=row["agent_id"],
                content=row["content"],
                embedding=row.get("embedding"),
                metadata=row.get("metadata", {}),
                timestamp=row.get("timestamp", datetime.utcnow()),
                importance_score=row.get("importance_score", 0.5),
                memory_type=row.get("memory_type", "episodic"),
                tags=row.get("tags", []),
            )
            results.append(
                MemorySearchResult(
                    memory=memory,
                    similarity=row.get("similarity", 0.0),
                    rank=rank,
                )
            )
        return results

    def get_by_id(self, memory_id: int) -> Memory | None:
        """Get a memory by its ID."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM synapse_memories WHERE id = %s AND deleted_at IS NULL",
                (memory_id,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        return Memory(
            id=row["id"],
            agent_id=row["agent_id"],
            content=row["content"],
            embedding=row.get("embedding"),
            metadata=row.get("metadata", {}),
            timestamp=row.get("timestamp", datetime.utcnow()),
            importance_score=row.get("importance_score", 0.5),
            memory_type=row.get("memory_type", "episodic"),
            tags=row.get("tags", []),
        )

    def log_access(self, memory_id: int, agent_id: str, context: dict[str, Any] | None = None):
        """Log access to a memory for audit trail."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO memory_access_log (memory_id, agent_id, context)
                   VALUES (%s, %s, %s)""",
                (memory_id, agent_id, psycopg2.extras.Json(context or {})),
            )
            conn.commit()

    def delete_memory(self, memory_id: int, reason: str = ""):
        """Soft delete a memory."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE synapse_memories SET deleted_at = NOW(), deletion_reason = %s WHERE id = %s",
                (reason, memory_id),
            )
            conn.commit()

    def delete_by_customer(self, customer_id: str) -> int:
        """GDPR Right to Erasure - delete all memories for a customer."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE synapse_memories SET deleted_at = NOW(), deletion_reason = 'GDPR erasure'
                   WHERE metadata->>'customer_id' = %s AND deleted_at IS NULL
                   RETURNING id""",
                (customer_id,),
            )
            deleted = cur.fetchall()
            conn.commit()
            return len(deleted)

    def get_statistics(self, agent_id: str) -> dict[str, Any]:
        """Get memory statistics for an agent."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT
                     agent_id,
                     COUNT(*) as total_memories,
                     COUNT(*) FILTER (WHERE deleted_at IS NULL) as active_memories,
                     COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) as deleted_memories,
                     AVG(importance_score) as avg_importance,
                     MAX(created_at) as last_memory_at,
                     MIN(created_at) as first_memory_at
                   FROM synapse_memories
                   WHERE agent_id = %s
                   GROUP BY agent_id""",
                (agent_id,),
            )
            row = cur.fetchone()

        if row is None:
            return {}
        return dict(row)

    def consolidate_memories(
        self,
        agent_id: str,
        source_memory_ids: list[int],
        consolidated_content: str,
        consolidated_embedding: Any,
        strategy: str = "summarization",
    ) -> int:
        """Consolidate multiple memories into one."""
        conn = self._get_connection()
        # Store consolidated memory
        consolidated_id = self.store(
            agent_id=agent_id,
            content=consolidated_content,
            embedding=consolidated_embedding,
            metadata={"consolidated_from": source_memory_ids, "strategy": strategy},
            importance_score=0.8,
            memory_type="consolidated",
        )

        # Mark source memories as consolidated
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE synapse_memories
                   SET metadata = metadata || %s
                   WHERE id = ANY(%s)""",
                (psycopg2.extras.Json({"consolidated_into": consolidated_id}), source_memory_ids),
            )
            conn.commit()

        return consolidated_id


def create_memory_store(connection_string: str | None = None) -> MemoryStore:
    """Create a MemoryStore instance."""
    return MemoryStore(connection_string=connection_string)
