"""Tests for LLM provider abstraction layer."""

import json
from unittest.mock import MagicMock, patch

import pytest

from neutron.agents.providers.base import LLMProvider, LLMResponse, ProviderConfig


class TestProviderConfig:
    def test_defaults(self):
        cfg = ProviderConfig(base_url="http://localhost:8080", model="test")
        assert cfg.base_url == "http://localhost:8080"
        assert cfg.model == "test"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 2048
        assert cfg.timeout == 30.0
        assert cfg.top_p == 0.9

    def test_custom_values(self):
        cfg = ProviderConfig(
            base_url="http://remote:9090",
            model="big-model",
            temperature=0.1,
            max_tokens=512,
            top_p=0.9,
            timeout=120,
        )
        assert cfg.temperature == 0.1
        assert cfg.max_tokens == 512
        assert cfg.top_p == 0.9
        assert cfg.timeout == 120


class TestLLMResponse:
    def test_basic(self):
        resp = LLMResponse(content="hello", model="m1")
        assert resp.content == "hello"
        assert resp.model == "m1"
        assert resp.finish_reason == "stop"
        assert resp.total_tokens == 0

    def test_with_usage(self):
        resp = LLMResponse(
            content="world",
            model="m2",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        assert resp.prompt_tokens == 10
        assert resp.completion_tokens == 5
        assert resp.total_tokens == 15


class TestLLMProviderABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            LLMProvider(ProviderConfig(base_url="x", model="y"))


# --- LlamaCppProvider tests (mocked HTTP) ---

class TestLlamaCppProvider:
    @pytest.fixture
    def mock_urlopen(self):
        """Mock urllib.request.urlopen to avoid real HTTP calls."""
        with patch("neutron.agents.providers.llamacpp.urlopen") as mock:
            yield mock

    def _make_chat_response(self, content: str = "test reply") -> bytes:
        return json.dumps({
            "choices": [
                {"message": {"content": content}, "finish_reason": "stop"}
            ],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }).encode()

    @pytest.fixture
    def provider(self):
        from neutron.agents.providers.llamacpp import LlamaCppProvider
        return LlamaCppProvider(base_url="http://test:8081", model="test-model")

    def test_init_defaults(self):
        from neutron.agents.providers.llamacpp import LlamaCppProvider
        p = LlamaCppProvider()
        assert "localhost" in p.config.base_url or "8081" in p.config.base_url

    def test_repr(self, provider):
        r = repr(provider)
        assert "LlamaCppProvider" in r
        assert "test:8081" in r

    @pytest.mark.asyncio
    async def test_generate(self, provider, mock_urlopen):
        ctx = MagicMock()
        ctx.read.return_value = self._make_chat_response("hello world")
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = ctx

        resp = await provider.generate("say hello", system="be nice")
        assert resp.content == "hello world"
        assert resp.model == "test-model"
        assert resp.total_tokens == 15

    @pytest.mark.asyncio
    async def test_generate_chat(self, provider, mock_urlopen):
        ctx = MagicMock()
        ctx.read.return_value = self._make_chat_response("chat reply")
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = ctx

        messages = [
            {"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "hi"},
        ]
        resp = await provider.generate_chat(messages)
        assert resp.content == "chat reply"

    @pytest.mark.asyncio
    async def test_health_ok(self, provider, mock_urlopen):
        ctx = MagicMock()
        ctx.read.return_value = json.dumps({"status": "ok"}).encode()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = ctx

        assert await provider.health() is True

    @pytest.mark.asyncio
    async def test_health_fail(self, provider, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("connection refused")

        assert await provider.health() is False

    @pytest.mark.asyncio
    async def test_embed(self, provider, mock_urlopen):
        ctx = MagicMock()
        ctx.read.return_value = json.dumps({
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }).encode()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = ctx

        embedding = await provider.embed("test text")
        assert embedding == [0.1, 0.2, 0.3]
