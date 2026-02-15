"""
LLM Provider implementations for NEXUS platform.

Each provider implements the same interface (LLMProvider) with
generate() and generate_chat() methods, enabling seamless fallback.

Supported: Anthropic (Claude), OpenAI (GPT), DeepSeek, llama.cpp
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("neutron.agents.providers")


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""

    content: str
    model: str
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    raw: Any = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def health(self) -> bool:
        ...


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: float = 30.0,
        **kwargs,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client = None
        self._api_key = api_key

    def _get_client(self):
        if self._client is None:
            import anthropic

            kwargs = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature
        else:
            kwargs["temperature"] = self.temperature
        if stop:
            kwargs["stop_sequences"] = stop

        response = await client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            finish_reason=response.stop_reason or "stop",
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            raw=response,
        )

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        client = self._get_client()

        # Extract system message if present
        system = None
        chat_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)

        if not chat_messages:
            chat_messages = [{"role": "user", "content": "Hello"}]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": chat_messages,
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature
        else:
            kwargs["temperature"] = self.temperature
        if stop:
            kwargs["stop_sequences"] = stop

        response = await client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            finish_reason=response.stop_reason or "stop",
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            raw=response,
        )

    async def health(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"AnthropicProvider(model={self.model})"


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4",
        base_url: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: float = 30.0,
        **kwargs,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client = None
        self._api_key = api_key
        self._base_url = base_url

    def _get_client(self):
        if self._client is None:
            import openai

            kwargs = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self.generate_chat(
            messages, temperature=temperature, max_tokens=max_tokens, stop=stop
        )

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        client = self._get_client()

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if max_tokens or self.max_tokens:
            kwargs["max_tokens"] = max_tokens or self.max_tokens
        if stop:
            kwargs["stop"] = stop

        response = await client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            finish_reason=choice.finish_reason or "stop",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            raw=response,
        )

    async def health(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"OpenAIProvider(model={self.model})"


class MLOffloadProvider(LLMProvider):
    """ML-Offload-API provider (local OpenAI-compatible inference server).

    Connects to the ml-offload-api at localhost:9000 which orchestrates
    local backends (Ollama, llama.cpp, vLLM, TGI) with VRAM management.
    """

    def __init__(
        self,
        api_key: str = "not-needed",
        model: str = "current-model",
        base_url: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: float = 60.0,
        **kwargs,
    ):
        import os

        if not base_url:
            host = os.getenv("ML_OFFLOAD_HOST", "127.0.0.1")
            port = os.getenv("ML_OFFLOAD_PORT", "9000")
            base_url = f"http://{host}:{port}/v1"

        self._openai = OpenAIProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        self.model = model
        self.base_url = base_url

    async def generate(self, prompt, **kwargs) -> LLMResponse:
        return await self._openai.generate(prompt, **kwargs)

    async def generate_chat(self, messages, **kwargs) -> LLMResponse:
        return await self._openai.generate_chat(messages, **kwargs)

    async def health(self) -> bool:
        try:
            # Check ml-offload-api health endpoint
            import aiohttp

            url = self.base_url.replace("/v1", "/health")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except Exception:
            return await self._openai.health()

    def __repr__(self) -> str:
        return f"MLOffloadProvider(model={self.model}, url={self.base_url})"


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider (OpenAI-compatible API)."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com/v1",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: float = 30.0,
        **kwargs,
    ):
        self._openai = OpenAIProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        self.model = model

    async def generate(self, prompt, **kwargs) -> LLMResponse:
        return await self._openai.generate(prompt, **kwargs)

    async def generate_chat(self, messages, **kwargs) -> LLMResponse:
        return await self._openai.generate_chat(messages, **kwargs)

    async def health(self) -> bool:
        return await self._openai.health()

    def __repr__(self) -> str:
        return f"DeepSeekProvider(model={self.model})"


class LlamaCppProvider(LLMProvider):
    """llama.cpp local server provider (OpenAI-compatible API)."""

    def __init__(
        self,
        api_key: str = "not-needed",
        model: str = "current-model",
        base_url: str = "http://localhost:8080/v1",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: float = 60.0,
        **kwargs,
    ):
        self._openai = OpenAIProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        self.model = model

    async def generate(self, prompt, **kwargs) -> LLMResponse:
        return await self._openai.generate(prompt, **kwargs)

    async def generate_chat(self, messages, **kwargs) -> LLMResponse:
        return await self._openai.generate_chat(messages, **kwargs)

    async def health(self) -> bool:
        return await self._openai.health()

    def __repr__(self) -> str:
        return f"LlamaCppProvider(model={self.model})"
