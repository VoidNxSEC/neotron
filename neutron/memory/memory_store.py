"""
SYNAPSE Memory Store - pgvector-based Semantic Memory

Long-term memory storage with semantic search using PostgreSQL + pgvector.

This provides persistent, searchable memory for AI agents with:
- Semantic similarity search via embeddings
- Importance scoring and memory consolidation
- GDPR-compliant soft deletion
- Access tracking for importance updates
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timedelta
import psycopg2
import psycopg2.extras
import numpy as np
import os


# =============================================================================
# Data Models
# =============================================================================

MemoryType = Literal["episodic", "semantic", "procedural"]


@dataclass
class Memory:
    """
    Single memory entry

    Attributes:
        id: Database ID (None for new memories)
        agent_id: ID of agent that owns this memory
        content: Text content of the memory
        embedding: Vector embedding for semantic search
        metadata: Additional structured data
        timestamp: When memory was created
        importance_score: Importance/relevance score (0.0-1.0)
        memory_type: Type of memory (episodic/semantic/procedural)
        tags: List of tags for categorization
    """
    id: Optional[int]
    agent_id: str
    content: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    importance_score: float = 0.5
    memory_type: MemoryType = "episodic"
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate importance score"""
        if not 0.0 <= self.importance_score <= 1.0:
            raise ValueError(
                f"Importance score must be between 0.0 and 1.0, got {self.importance_score}"
            )


@dataclass
class MemorySearchResult:
    """
    Result from semantic search

    Attributes:
        memory: The memory that was found
        similarity: Cosine similarity score (0.0-1.0)
        rank: Rank in search results (1-indexed)
    """
    memory: Memory
    similarity: float
    rank: int


# =============================================================================
# Memory Store
# =============================================================================

class MemoryStore:
    """
    Long-term memory storage with semantic search

    Uses PostgreSQL + pgvector for persistent, searchable memory.

    Example:
        >>> store = MemoryStore()
        >>> memory_id = store.store(
        ...     agent_id="agent_1",
        ...     content="Customer prefers low-risk investments",
        ...     embedding=embed("Customer prefers low-risk investments"),
        ...     metadata={"customer_id": "12345"}
        ... )
        >>> results = store.search(
        ...     query_embedding=embed("What are customer preferences?"),
        ...     agent_id="agent_1",
        ...     top_k=5
        ... )
    """

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize memory store

        Args:
            connection_string: PostgreSQL connection string
                              (defaults to DATABASE_URL env var)
        """
        self.connection_string = connection_string or os.environ.get(
            "DATABASE_URL",
            "postgresql://neutron:neutron_dev_password@localhost:5432/neutron"
        )

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)

    def store(
        self,
        agent_id: str,
        content: str,
        embedding: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None,
        importance_score: float = 0.5,
        memory_type: MemoryType = "episodic",
        tags: Optional[List[str]] = None
    ) -> int:
        """
        Store memory

        Args:
            agent_id: ID of agent
            content: Text content
            embedding: Vector embedding (numpy array)
            metadata: Additional data
            importance_score: Importance (0.0-1.0)
            memory_type: Type of memory
            tags: Optional tags

        Returns:
            Memory ID (database PK)
        """
        if not 0.0 <= importance_score <= 1.0:
            raise ValueError(f"Importance must be 0.0-1.0, got {importance_score}")

        # Convert numpy array to list for PostgreSQL
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_memories (
                        agent_id,
                        content,
                        embedding,
                        metadata,
                        importance_score,
                        memory_type,
                        tags
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        agent_id,
                        content,
                        embedding_list,
                        psycopg2.extras.Json(metadata or {}),
                        importance_score,
                        memory_type,
                        tags or []
                    )
                )
                memory_id = cur.fetchone()[0]
                conn.commit()
                return memory_id
        finally:
            conn.close()

    def search(
        self,
        query_embedding: np.ndarray,
        agent_id: Optional[str] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        time_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[MemorySearchResult]:
        """
        Semantic search for similar memories

        Args:
            query_embedding: Query vector
            agent_id: Filter by agent ID (None = all agents)
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            memory_type: Filter by memory type
            tags: Filter by tags (any match)
            time_range: Filter by time range (start, end)

        Returns:
            List of MemorySearchResult ordered by similarity
        """
        # Convert numpy array to list for PostgreSQL
        embedding_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding

        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Build WHERE clause
                where_conditions = ["deleted_at IS NULL"]
                params = [embedding_list, top_k]

                if agent_id:
                    where_conditions.append("agent_id = %s")
                    params.append(agent_id)

                if memory_type:
                    where_conditions.append("memory_type = %s")
                    params.append(memory_type)

                if tags:
                    where_conditions.append("tags && %s")  # Array overlap operator
                    params.append(tags)

                if time_range:
                    where_conditions.append("timestamp BETWEEN %s AND %s")
                    params.extend(time_range)

                where_clause = " AND ".join(where_conditions)

                # Use pgvector cosine distance operator (<=>)
                # Similarity = 1 - distance
                query = f"""
                    SELECT
                        id,
                        agent_id,
                        content,
                        embedding,
                        metadata,
                        timestamp,
                        importance_score,
                        memory_type,
                        tags,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM agent_memories
                    WHERE {where_clause}
                      AND (1 - (embedding <=> %s::vector)) >= {similarity_threshold}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """

                # Need embedding 3 times: for similarity calc, WHERE filter, ORDER BY
                cur.execute(query, [embedding_list, embedding_list, embedding_list] + params)
                rows = cur.fetchall()

                # Convert to MemorySearchResult objects
                results = []
                for rank, row in enumerate(rows, start=1):
                    # Convert embedding back to numpy array
                    embedding_array = np.array(row['embedding'])

                    memory = Memory(
                        id=row['id'],
                        agent_id=row['agent_id'],
                        content=row['content'],
                        embedding=embedding_array,
                        metadata=row['metadata'],
                        timestamp=row['timestamp'],
                        importance_score=row['importance_score'],
                        memory_type=row['memory_type'],
                        tags=row['tags']
                    )

                    results.append(MemorySearchResult(
                        memory=memory,
                        similarity=float(row['similarity']),
                        rank=rank
                    ))

                return results
        finally:
            conn.close()

    def get_by_id(self, memory_id: int) -> Optional[Memory]:
        """
        Get memory by ID

        Args:
            memory_id: Memory ID

        Returns:
            Memory or None if not found
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM agent_memories
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (memory_id,)
                )
                row = cur.fetchone()

                if not row:
                    return None

                return Memory(
                    id=row['id'],
                    agent_id=row['agent_id'],
                    content=row['content'],
                    embedding=np.array(row['embedding']),
                    metadata=row['metadata'],
                    timestamp=row['timestamp'],
                    importance_score=row['importance_score'],
                    memory_type=row['memory_type'],
                    tags=row['tags']
                )
        finally:
            conn.close()

    def log_access(
        self,
        memory_id: int,
        agent_id: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log memory access (updates importance score via trigger)

        Args:
            memory_id: Memory ID that was accessed
            agent_id: Agent that accessed it
            context: Optional context about the access
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO memory_access_log (
                        memory_id,
                        agent_id,
                        access_context
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (memory_id, agent_id, psycopg2.extras.Json(context or {}))
                )
                conn.commit()
        finally:
            conn.close()

    def delete_memory(
        self,
        memory_id: int,
        reason: str = "User requested deletion"
    ):
        """
        Soft delete memory (GDPR compliance)

        Args:
            memory_id: Memory ID to delete
            reason: Reason for deletion
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_memories
                    SET deleted_at = NOW(),
                        deletion_reason = %s
                    WHERE id = %s
                    """,
                    (reason, memory_id)
                )
                conn.commit()
        finally:
            conn.close()

    def delete_by_customer(self, customer_id: str) -> int:
        """
        Delete all memories for a customer (GDPR Right to Erasure)

        Args:
            customer_id: Customer ID (from metadata)

        Returns:
            Number of memories deleted
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_memories
                    SET deleted_at = NOW(),
                        deletion_reason = 'GDPR Article 17 - Right to Erasure'
                    WHERE metadata->>'customer_id' = %s
                      AND deleted_at IS NULL
                    RETURNING id
                    """,
                    (customer_id,)
                )
                deleted_ids = cur.fetchall()
                conn.commit()
                return len(deleted_ids)
        finally:
            conn.close()

    def get_statistics(self, agent_id: str) -> Dict[str, Any]:
        """
        Get memory statistics for an agent

        Args:
            agent_id: Agent ID

        Returns:
            Statistics dict
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM memory_statistics
                    WHERE agent_id = %s
                    """,
                    (agent_id,)
                )
                row = cur.fetchone()
                return dict(row) if row else {}
        finally:
            conn.close()

    def consolidate_memories(
        self,
        agent_id: str,
        source_memory_ids: List[int],
        consolidated_content: str,
        consolidated_embedding: np.ndarray,
        strategy: str = "summarization"
    ) -> int:
        """
        Consolidate multiple memories into one

        Args:
            agent_id: Agent ID
            source_memory_ids: IDs of memories being consolidated
            consolidated_content: New consolidated content
            consolidated_embedding: Embedding for consolidated memory
            strategy: Consolidation strategy used

        Returns:
            ID of consolidated memory
        """
        # Store consolidated memory
        consolidated_id = self.store(
            agent_id=agent_id,
            content=consolidated_content,
            embedding=consolidated_embedding,
            metadata={"consolidated_from": source_memory_ids},
            importance_score=0.8,  # Higher importance for consolidated memories
            memory_type="semantic"  # Consolidations are semantic
        )

        # Log consolidation
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO memory_consolidations (
                        agent_id,
                        source_memory_ids,
                        consolidated_memory_id,
                        consolidation_strategy
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (agent_id, source_memory_ids, consolidated_id, strategy)
                )
                conn.commit()
        finally:
            conn.close()

        return consolidated_id


# =============================================================================
# Utility Functions
# =============================================================================

def create_memory_store(connection_string: Optional[str] = None) -> MemoryStore:
    """
    Convenience function to create memory store

    Args:
        connection_string: PostgreSQL connection string

    Returns:
        MemoryStore instance
    """
    return MemoryStore(connection_string)
