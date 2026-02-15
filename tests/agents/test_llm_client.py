"""
Tests for LLM client with fallback chain and circuit breakers.
"""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

from neutron.agents.llm_client import LLMClient, CircuitBreakerState
from neutron.agents.providers import LLMResponse
from neutron.core.config import LLMConfig, ProviderType, ProviderConfig


@pytest.fixture
def mock_config():
    """Create mock LLM configuration."""
    config = LLMConfig(
        primary_provider=ProviderType.ANTHROPIC,
        fallback_chain=[ProviderType.DEEPSEEK, ProviderType.OPENAI],
        enable_retries=True,
        enable_circuit_breaker=True,
    )

    # Configure providers
    for provider_type in ProviderType:
        config.providers[provider_type] = ProviderConfig(
            provider_type=provider_type,
            enabled=True,
            api_key="test-key",
            model="test-model",
            max_retries=2,
            circuit_breaker_threshold=3,
        )

    return config


def test_circuit_breaker_state():
    """Test circuit breaker state management."""
    cb = CircuitBreakerState(threshold=3, timeout=60.0)

    assert cb.can_attempt() is True
    assert cb.is_open is False

    # Record failures
    cb.record_failure()
    assert cb.failures == 1
    assert cb.is_open is False

    cb.record_failure()
    cb.record_failure()
    assert cb.failures == 3
    assert cb.is_open is True
    assert cb.can_attempt() is False

    # Record success resets
    cb.record_success()
    assert cb.failures == 0
    assert cb.is_open is False
    assert cb.can_attempt() is True


@pytest.mark.asyncio
async def test_llm_client_initialization(mock_config):
    """Test LLM client initializes providers correctly."""
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "test-anthropic",
        "OPENAI_API_KEY": "test-openai",
        "DEEPSEEK_API_KEY": "test-deepseek",
    }):
        client = LLMClient(config=mock_config)

        # Should have circuit breakers for each provider
        assert len(client._circuit_breakers) >= 1


@pytest.mark.asyncio
async def test_llm_client_fallback(mock_config):
    """Test fallback chain when primary provider fails."""
    client = LLMClient(config=mock_config)

    # Mock provider responses
    mock_response = LLMResponse(
        content="Test response",
        model="test-model",
        total_tokens=10,
    )

    # Mock first provider to fail, second to succeed
    with patch.object(client, "_call_provider") as mock_call:
        mock_call.side_effect = [
            RuntimeError("Primary failed"),
            mock_response,
        ]

        response = await client.generate("test prompt")

        assert response.content == "Test response"
        # Should have tried two providers
        assert mock_call.call_count == 2


@pytest.mark.asyncio
async def test_llm_client_all_providers_fail(mock_config):
    """Test error when all providers fail."""
    client = LLMClient(config=mock_config)

    with patch.object(client, "_call_provider") as mock_call:
        mock_call.side_effect = RuntimeError("All failed")

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            await client.generate("test prompt")


@pytest.mark.asyncio
async def test_llm_client_circuit_breaker_blocks(mock_config):
    """Test circuit breaker blocks provider after threshold failures."""
    client = LLMClient(config=mock_config)

    # Manually open circuit breaker for primary provider
    primary = mock_config.primary_provider
    if primary in client._circuit_breakers:
        client._circuit_breakers[primary].is_open = True
        client._circuit_breakers[primary].failures = 5

    mock_response = LLMResponse(content="Fallback response", model="fallback", total_tokens=5)

    with patch.object(client, "_call_provider") as mock_call:
        # Primary should be skipped, fallback should be called
        mock_call.return_value = mock_response

        response = await client.generate("test prompt")

        # Should skip primary and use fallback
        assert response.content == "Fallback response"


@pytest.mark.asyncio
async def test_llm_client_health_check():
    """Test health check for all providers."""
    client = LLMClient()

    # Mock provider health checks
    for provider_type, provider in client._providers.items():
        if hasattr(provider, "health"):
            with patch.object(provider, "health", new_callable=AsyncMock) as mock_health:
                mock_health.return_value = True

    health = await client.health_check()

    # Should return health status for all providers
    assert isinstance(health, dict)


@pytest.mark.asyncio
async def test_llm_client_retry_logic(mock_config):
    """Test retry logic with exponential backoff."""
    client = LLMClient(config=mock_config)

    mock_response = LLMResponse(content="Success after retry", model="test", total_tokens=10)

    call_count = 0

    async def mock_provider_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RuntimeError("Temporary failure")
        return mock_response

    with patch.object(client._providers.get(ProviderType.ANTHROPIC, MagicMock()), "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = mock_provider_call

        # This test requires actual provider initialization which may fail
        # without API keys. Skip if provider not available.
        if ProviderType.ANTHROPIC not in client._providers:
            pytest.skip("Anthropic provider not available")


def test_circuit_breaker_status():
    """Test getting circuit breaker status."""
    client = LLMClient()

    status = client.get_circuit_breaker_status()

    assert isinstance(status, dict)
    # Each provider should have circuit breaker status
    for provider_status in status.values():
        assert "is_open" in provider_status
        assert "failures" in provider_status
        assert "threshold" in provider_status
