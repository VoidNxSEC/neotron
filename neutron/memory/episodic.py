"""
Synapse Episodic Memory - PostgreSQL + pgvector Implementation
"""
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import sqlalchemy
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB

# Configure logging
logger = logging.getLogger("neutron.memory.episodic")

Base = declarative_base()

class MemoryModel(Base):
    __tablename__ = "synapse_memory"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String, index=True)
    content = Column(String, nullable=False)
    # Vector column would be: embedding = Column(Vector(1536)) - requires pgvector-python
    # For now using raw SQL for vector operations to minimize dependency friction
    embedding = Column(JSONB) # Storing as device-independent JSON for now, can perform exact match or use specialized index
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

class EpisodicMemory:
    """
    Real persistence layer for Agent Memory.
    Uses PostgreSQL for structured storage and planned pgvector integration.
    """
    def __init__(self, connection_string: str = "postgresql://neutron:neutron@localhost:5432/temporal"):
        self.engine = create_engine(connection_string, pool_size=5, max_overflow=10)
        self.Session = sessionmaker(bind=self.engine)
        self._init_db()

    def _init_db(self):
        """Initialize database schema and extensions."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            Base.metadata.create_all(self.engine)
            logger.info("Synapse memory schema initialized.")
        except Exception as e:
            logger.error(f"Failed to init DB (is Postgres running?): {e}")

    def store(self, agent_id: str, content: str, embedding: Optional[List[float]] = None, meta: Dict = None):
        """Store a memory episode."""
        session = self.Session()
        try:
            entry = MemoryModel(
                agent_id=agent_id,
                content=content,
                # embedding=embedding, # TODO: Serialize for pgvector
                metadata_=meta or {}
            )
            session.add(entry)
            session.commit()
            return entry.id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store memory: {e}")
            raise
        finally:
            session.close()

    def search(self, query_embedding: List[float], limit: int = 5, agent_id: str = None) -> List[Dict]:
        """
        Semantic search using vector similarity.
        (Currently simulated with latest-k retrieval until pgvector logic is fully wired)
        """
        session = self.Session()
        try:
            # Placeholder for vector search: Retrieve recent memories for context
            q = session.query(MemoryModel).order_by(MemoryModel.created_at.desc())
            if agent_id:
                q = q.filter(MemoryModel.agent_id == agent_id)
            
            results = q.limit(limit).all()
            
            return [{
                "id": r.id,
                "content": r.content,
                "created_at": r.created_at.isoformat(),
                "score": 1.0 # Placeholder score
            } for r in results]
        finally:
            session.close()

    def get_stats(self):
        session = self.Session()
        try:
            count = session.query(MemoryModel).count()
            return {"total_memories": count}
        finally:
            session.close()
