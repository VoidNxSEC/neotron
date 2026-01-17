"""
Tests for SYNAPSE Working Memory
"""
import pytest
from neutron.memory.working import WorkingMemory


def test_working_memory_add():
    """Test adding messages to working memory"""
    wm = WorkingMemory(max_tokens=1000)
    wm.add_message("system", "You are a helpful assistant")
    wm.add_message("user", "Hello")
    
    assert len(wm.messages) == 2
    assert wm.messages[0].role == "system"
    assert wm.messages[1].role == "user"
    assert wm.total_tokens > 0


def test_working_memory_truncation():
    """Test sliding window truncation when max_tokens exceeded"""
    # Each char ~0.25 tokens, so 40 chars ~10 tokens
    # We set max_tokens to 15 to trigger truncation quickly
    wm = WorkingMemory(max_tokens=15)
    
    wm.add_message("system", "System prompt") # ~3 tokens
    wm.add_message("user", "Hello world this is a test") # ~6 tokens
    wm.add_message("assistant", "I am an assistant") # ~4 tokens
    # Total so far: ~13 tokens
    
    assert len(wm.messages) == 3
    
    # This should trigger truncation of the oldest message (after system)
    wm.add_message("user", "Another message that is quite long indeed") # ~10 tokens
    # Total: 13 + 10 = 23 > 15
    
    # Should have removed the second message (first after system)
    assert len(wm.messages) < 4
    assert wm.messages[0].role == "system"
    assert "Hello world" not in [m.content for m in wm.messages]


def test_working_memory_get_context():
    """Test retrieval of context in standard format"""
    wm = WorkingMemory()
    wm.add_message("user", "Hi")
    wm.add_message("assistant", "Hello!")
    
    context = wm.get_context()
    assert context == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"}
    ]
