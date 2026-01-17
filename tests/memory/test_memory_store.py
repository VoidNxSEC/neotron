"""
Tests for SYNAPSE Memory Store

Tests semantic search, memory storage, and GDPR compliance features.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from neutron.memory import (
    MemoryStore,
    Memory,
    MemorySearchResult,
    create_memory_store,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_connection():
    """Mock PostgreSQL connection"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor


@pytest.fixture
def sample_embedding():
    """Sample 1536-dimensional embedding"""
    return np.random.rand(1536)


@pytest.fixture
def sample_memory(sample_embedding):
    """Sample memory object"""
    return Memory(
        id=1,
        agent_id="agent_1",
        content="Customer prefers low-risk investments",
        embedding=sample_embedding,
        metadata={"customer_id": "12345"},
        timestamp=datetime.utcnow(),
        importance_score=0.75,
        memory_type="episodic",
        tags=["preference", "investment"]
    )


# =============================================================================
# Memory Data Model Tests
# =============================================================================

class TestMemory:
    """Tests for Memory data model"""

    def test_create_memory(self, sample_embedding):
        """Test creating valid memory"""
        memory = Memory(
            id=1,
            agent_id="agent_1",
            content="Test memory",
            embedding=sample_embedding,
            metadata={"key": "value"},
            importance_score=0.8
        )

        assert memory.id == 1
        assert memory.agent_id == "agent_1"
        assert memory.content == "Test memory"
        assert memory.importance_score == 0.8
        assert memory.metadata == {"key": "value"}

    def test_importance_score_validation(self, sample_embedding):
        """Test importance score must be 0.0-1.0"""
        # Valid scores
        Memory(id=None, agent_id="a", content="x", embedding=sample_embedding, importance_score=0.0)
        Memory(id=None, agent_id="a", content="x", embedding=sample_embedding, importance_score=1.0)
        Memory(id=None, agent_id="a", content="x", embedding=sample_embedding, importance_score=0.5)

        # Invalid scores
        with pytest.raises(ValueError, match="Importance score"):
            Memory(id=None, agent_id="a", content="x", embedding=sample_embedding, importance_score=-0.1)

        with pytest.raises(ValueError, match="Importance score"):
            Memory(id=None, agent_id="a", content="x", embedding=sample_embedding, importance_score=1.1)

    def test_memory_defaults(self, sample_embedding):
        """Test memory default values"""
        memory = Memory(
            id=None,
            agent_id="agent_1",
            content="Test",
            embedding=sample_embedding
        )

        assert memory.metadata == {}
        assert memory.importance_score == 0.5
        assert memory.memory_type == "episodic"
        assert memory.tags == []
        assert isinstance(memory.timestamp, datetime)


# =============================================================================
# MemoryStore Tests (Mocked)
# =============================================================================

class TestMemoryStoreMocked:
    """Tests for MemoryStore with mocked database"""

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_store_memory(self, mock_connect, mock_connection, sample_embedding):
        """Test storing memory"""
        mock_conn, mock_cursor = mock_connection
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = [42]

        store = MemoryStore()
        memory_id = store.store(
            agent_id="agent_1",
            content="Test content",
            embedding=sample_embedding,
            metadata={"key": "value"},
            importance_score=0.8,
            tags=["tag1", "tag2"]
        )

        assert memory_id == 42
        assert mock_cursor.execute.called
        assert mock_conn.commit.called

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_store_invalid_importance(self, mock_connect, sample_embedding):
        """Test storing memory with invalid importance score"""
        store = MemoryStore()

        with pytest.raises(ValueError, match="Importance"):
            store.store(
                agent_id="agent_1",
                content="Test",
                embedding=sample_embedding,
                importance_score=1.5
            )

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_search_memories(self, mock_connect, mock_connection, sample_embedding):
        """Test searching memories"""
        mock_conn, mock_cursor = mock_connection
        mock_connect.return_value = mock_conn

        # Mock search results
        mock_cursor.fetchall.return_value = [
            {
                'id': 1,
                'agent_id': 'agent_1',
                'content': 'Memory 1',
                'embedding': sample_embedding.tolist(),
                'metadata': {'key': 'value'},
                'timestamp': datetime.utcnow(),
                'importance_score': 0.8,
                'memory_type': 'episodic',
                'tags': ['tag1'],
                'similarity': 0.95
            },
            {
                'id': 2,
                'agent_id': 'agent_1',
                'content': 'Memory 2',
                'embedding': sample_embedding.tolist(),
                'metadata': {},
                'timestamp': datetime.utcnow(),
                'importance_score': 0.7,
                'memory_type': 'semantic',
                'tags': [],
                'similarity': 0.85
            }
        ]

        store = MemoryStore()
        results = store.search(
            query_embedding=sample_embedding,
            agent_id="agent_1",
            top_k=10
        )

        assert len(results) == 2
        assert isinstance(results[0], MemorySearchResult)
        assert results[0].similarity == 0.95
        assert results[0].rank == 1
        assert results[1].rank == 2

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_get_by_id(self, mock_connect, mock_connection, sample_embedding):
        """Test getting memory by ID"""
        mock_conn, mock_cursor = mock_connection
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = {
            'id': 1,
            'agent_id': 'agent_1',
            'content': 'Test memory',
            'embedding': sample_embedding.tolist(),
            'metadata': {'key': 'value'},
            'timestamp': datetime.utcnow(),
            'importance_score': 0.8,
            'memory_type': 'episodic',
            'tags': ['tag1']
        }

        store = MemoryStore()
        memory = store.get_by_id(1)

        assert memory is not None
        assert memory.id == 1
        assert memory.content == 'Test memory'
        assert memory.importance_score == 0.8

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_get_by_id_not_found(self, mock_connect, mock_connection):
        """Test getting non-existent memory"""
        mock_conn, mock_cursor = mock_connection
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = None

        store = MemoryStore()
        memory = store.get_by_id(999)

        assert memory is None

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_log_access(self, mock_connect, mock_connection):
        """Test logging memory access"""
        mock_conn, mock_cursor = mock_connection
        mock_connect.return_value = mock_conn

        store = MemoryStore()
        store.log_access(
            memory_id=1,
            agent_id="agent_1",
            context={"query": "test"}
        )

        assert mock_cursor.execute.called
        assert mock_conn.commit.called

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_delete_memory(self, mock_connect, mock_connection):
        """Test soft deleting memory"""
        mock_conn, mock_cursor = mock_connection
        mock_connect.return_value = mock_conn

        store = MemoryStore()
        store.delete_memory(
            memory_id=1,
            reason="Test deletion"
        )

        assert mock_cursor.execute.called
        assert mock_conn.commit.called

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_delete_by_customer(self, mock_connect, mock_connection):
        """Test GDPR Right to Erasure"""
        mock_conn, mock_cursor = mock_connection
        mock_connect.return_value = mock_conn

        # Mock 3 deleted memories
        mock_cursor.fetchall.return_value = [(1,), (2,), (3,)]

        store = MemoryStore()
        deleted_count = store.delete_by_customer(customer_id="12345")

        assert deleted_count == 3
        assert mock_cursor.execute.called
        assert mock_conn.commit.called

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_get_statistics(self, mock_connect, mock_connection):
        """Test getting memory statistics"""
        mock_conn, mock_cursor = mock_connection
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = {
            'agent_id': 'agent_1',
            'total_memories': 100,
            'active_memories': 95,
            'deleted_memories': 5,
            'avg_importance': 0.75,
            'last_memory_at': datetime.utcnow(),
            'first_memory_at': datetime.utcnow() - timedelta(days=30)
        }

        store = MemoryStore()
        stats = store.get_statistics(agent_id="agent_1")

        assert stats['total_memories'] == 100
        assert stats['active_memories'] == 95
        assert stats['avg_importance'] == 0.75

    @patch('neutron.memory.memory_store.psycopg2.connect')
    def test_consolidate_memories(self, mock_connect, mock_connection, sample_embedding):
        """Test memory consolidation"""
        mock_conn, mock_cursor = mock_connection
        mock_connect.return_value = mock_conn

        # Mock store returning ID 42 for consolidated memory
        mock_cursor.fetchone.return_value = [42]

        store = MemoryStore()

        # Mock the store method
        with patch.object(store, 'store', return_value=42):
            consolidated_id = store.consolidate_memories(
                agent_id="agent_1",
                source_memory_ids=[1, 2, 3],
                consolidated_content="Consolidated memory",
                consolidated_embedding=sample_embedding,
                strategy="summarization"
            )

            assert consolidated_id == 42
            assert mock_cursor.execute.called
            assert mock_conn.commit.called


# =============================================================================
# MemorySearchResult Tests
# =============================================================================

class TestMemorySearchResult:
    """Tests for MemorySearchResult"""

    def test_search_result(self, sample_memory):
        """Test creating search result"""
        result = MemorySearchResult(
            memory=sample_memory,
            similarity=0.95,
            rank=1
        )

        assert result.memory == sample_memory
        assert result.similarity == 0.95
        assert result.rank == 1


# =============================================================================
# Integration Tests (Require Real Database)
# =============================================================================

@pytest.mark.integration
class TestMemoryStoreIntegration:
    """Integration tests requiring real PostgreSQL with pgvector"""

    @pytest.fixture
    def store(self):
        """Create real memory store (requires DATABASE_URL)"""
        return MemoryStore()

    @pytest.fixture
    def cleanup_memories(self, store):
        """Cleanup test memories after each test"""
        yield
        # Cleanup would go here if needed

    def test_store_and_retrieve(self, store, sample_embedding):
        """Test storing and retrieving memory"""
        # Store memory
        memory_id = store.store(
            agent_id="test_agent",
            content="Integration test memory",
            embedding=sample_embedding,
            metadata={"test": True},
            importance_score=0.9
        )

        assert memory_id > 0

        # Retrieve by ID
        memory = store.get_by_id(memory_id)
        assert memory is not None
        assert memory.content == "Integration test memory"
        assert memory.importance_score == 0.9

    def test_semantic_search(self, store):
        """Test semantic similarity search"""
        # Store multiple memories
        embedding1 = np.random.rand(1536)
        embedding2 = np.random.rand(1536)

        id1 = store.store(
            agent_id="test_agent",
            content="Customer likes stocks",
            embedding=embedding1
        )

        id2 = store.store(
            agent_id="test_agent",
            content="Customer prefers bonds",
            embedding=embedding2
        )

        # Search with similar embedding to embedding1
        results = store.search(
            query_embedding=embedding1,
            agent_id="test_agent",
            top_k=5,
            similarity_threshold=0.5
        )

        assert len(results) > 0
        # First result should be the exact match
        assert results[0].memory.id == id1
        assert results[0].similarity > 0.99

    def test_access_logging(self, store, sample_embedding):
        """Test access logging updates importance"""
        # Store memory
        memory_id = store.store(
            agent_id="test_agent",
            content="Test memory",
            embedding=sample_embedding,
            importance_score=0.5
        )

        # Log access
        store.log_access(memory_id, "test_agent", {"query": "test"})

        # Importance should increase (via trigger)
        memory = store.get_by_id(memory_id)
        assert memory.importance_score > 0.5

    def test_gdpr_deletion(self, store, sample_embedding):
        """Test GDPR-compliant deletion"""
        # Store memory with customer ID
        memory_id = store.store(
            agent_id="test_agent",
            content="Customer data",
            embedding=sample_embedding,
            metadata={"customer_id": "test_customer_123"}
        )

        # Delete by customer
        deleted_count = store.delete_by_customer("test_customer_123")
        assert deleted_count >= 1

        # Memory should be soft-deleted
        memory = store.get_by_id(memory_id)
        assert memory is None  # Filtered out by deleted_at


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilityFunctions:
    """Tests for utility functions"""

    def test_create_memory_store(self):
        """Test create_memory_store convenience function"""
        store = create_memory_store()
        assert isinstance(store, MemoryStore)

    def test_create_memory_store_with_connection(self):
        """Test creating store with custom connection string"""
        store = create_memory_store("postgresql://custom:pass@localhost/db")
        assert isinstance(store, MemoryStore)
        assert store.connection_string == "postgresql://custom:pass@localhost/db"
