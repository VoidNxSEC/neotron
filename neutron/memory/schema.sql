-- SYNAPSE Memory Schema
-- Long-term memory storage with semantic search using pgvector

-- Create vector extension (if not exists)
CREATE EXTENSION IF NOT EXISTS vector;

-- Agent Memories Table
-- Stores all agent memories with embeddings for semantic search
CREATE TABLE IF NOT EXISTS agent_memories (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 dimension (can be changed)
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    importance_score FLOAT DEFAULT 0.5 CHECK (importance_score >= 0.0 AND importance_score <= 1.0),
    memory_type VARCHAR(50) DEFAULT 'episodic' CHECK (memory_type IN ('episodic', 'semantic', 'procedural')),
    tags TEXT[] DEFAULT '{}',

    -- Soft delete support (for GDPR compliance)
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    deletion_reason TEXT DEFAULT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON agent_memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON agent_memories(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON agent_memories(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_type ON agent_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON agent_memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memories_deleted ON agent_memories(deleted_at) WHERE deleted_at IS NULL;

-- Vector index for semantic search
-- Using ivfflat for approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON agent_memories
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Memory Consolidation Table
-- Tracks which memories have been consolidated/summarized
CREATE TABLE IF NOT EXISTS memory_consolidations (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    source_memory_ids INTEGER[] NOT NULL,
    consolidated_memory_id INTEGER NOT NULL REFERENCES agent_memories(id),
    consolidation_strategy VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_consolidation UNIQUE (agent_id, consolidated_memory_id)
);

CREATE INDEX IF NOT EXISTS idx_consolidations_agent_id ON memory_consolidations(agent_id);
CREATE INDEX IF NOT EXISTS idx_consolidations_timestamp ON memory_consolidations(timestamp DESC);

-- Memory Access Log Table
-- Tracks when memories are retrieved (for importance scoring)
CREATE TABLE IF NOT EXISTS memory_access_log (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER NOT NULL REFERENCES agent_memories(id),
    agent_id VARCHAR(255) NOT NULL,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    access_context JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_access_log_memory_id ON memory_access_log(memory_id);
CREATE INDEX IF NOT EXISTS idx_access_log_agent_id ON memory_access_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_access_log_timestamp ON memory_access_log(accessed_at DESC);

-- Views for common queries

-- Active Memories View (non-deleted)
CREATE OR REPLACE VIEW active_memories AS
SELECT *
FROM agent_memories
WHERE deleted_at IS NULL;

-- Recent Memories View
CREATE OR REPLACE VIEW recent_memories AS
SELECT *
FROM agent_memories
WHERE deleted_at IS NULL
  AND timestamp >= NOW() - INTERVAL '30 days'
ORDER BY timestamp DESC;

-- Important Memories View
CREATE OR REPLACE VIEW important_memories AS
SELECT *
FROM agent_memories
WHERE deleted_at IS NULL
  AND importance_score >= 0.7
ORDER BY importance_score DESC, timestamp DESC;

-- Memory Statistics View
CREATE OR REPLACE VIEW memory_statistics AS
SELECT
    agent_id,
    COUNT(*) as total_memories,
    COUNT(*) FILTER (WHERE deleted_at IS NULL) as active_memories,
    COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) as deleted_memories,
    AVG(importance_score) FILTER (WHERE deleted_at IS NULL) as avg_importance,
    MAX(timestamp) FILTER (WHERE deleted_at IS NULL) as last_memory_at,
    MIN(timestamp) FILTER (WHERE deleted_at IS NULL) as first_memory_at
FROM agent_memories
GROUP BY agent_id;

-- Functions

-- Function to update importance score based on access frequency
CREATE OR REPLACE FUNCTION update_importance_from_access()
RETURNS TRIGGER AS $$
BEGIN
    -- Increment importance score slightly on each access (max 1.0)
    UPDATE agent_memories
    SET importance_score = LEAST(importance_score + 0.01, 1.0)
    WHERE id = NEW.memory_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update importance on access
DROP TRIGGER IF EXISTS trg_update_importance_on_access ON memory_access_log;
CREATE TRIGGER trg_update_importance_on_access
AFTER INSERT ON memory_access_log
FOR EACH ROW
EXECUTE FUNCTION update_importance_from_access();

-- Function for semantic search
-- Returns memories similar to query embedding
CREATE OR REPLACE FUNCTION search_memories_by_embedding(
    p_embedding vector(1536),
    p_agent_id VARCHAR(255) DEFAULT NULL,
    p_top_k INTEGER DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    memory_id INTEGER,
    agent_id VARCHAR(255),
    content TEXT,
    similarity FLOAT,
    importance_score FLOAT,
    timestamp TIMESTAMPTZ,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id as memory_id,
        m.agent_id,
        m.content,
        1 - (m.embedding <=> p_embedding) as similarity,
        m.importance_score,
        m.timestamp,
        m.metadata
    FROM agent_memories m
    WHERE m.deleted_at IS NULL
      AND (p_agent_id IS NULL OR m.agent_id = p_agent_id)
      AND (1 - (m.embedding <=> p_embedding)) >= p_threshold
    ORDER BY m.embedding <=> p_embedding
    LIMIT p_top_k;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE agent_memories IS 'Long-term memory storage for AI agents with semantic search via pgvector';
COMMENT ON COLUMN agent_memories.embedding IS 'Vector embedding for semantic similarity search (default: 1536 dimensions for OpenAI ada-002)';
COMMENT ON COLUMN agent_memories.importance_score IS 'Importance score (0.0-1.0) for memory consolidation and retrieval priority';
COMMENT ON COLUMN agent_memories.memory_type IS 'Type of memory: episodic (events), semantic (facts), procedural (skills)';
COMMENT ON COLUMN agent_memories.deleted_at IS 'Soft delete timestamp for GDPR compliance (right to erasure)';

COMMENT ON VIEW memory_statistics IS 'Aggregate statistics per agent for monitoring memory usage';
COMMENT ON FUNCTION search_memories_by_embedding IS 'Semantic search using cosine similarity on vector embeddings';
