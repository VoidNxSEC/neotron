from __future__ import annotations

import json
import logging
from urllib.request import Request, urlopen

from neutron.agents._llm_http_client import LLMHTTPClient, _LLMResponse
from neutron.agents.providers.base import ProviderConfig

logger = logging.getLogger("neutron.agents.providers.llamacpp")


class LlamaCppProvider:
    """LLM provider backed by a llama.cpp / llama-swap HTTP server."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._client = LLMHTTPClient()
        self._client.base_url = config.base_url
        self._client._model = config.model

    async def health(self) -> bool:
        """Return True if the llama.cpp server is reachable."""
        try:
            import asyncio

            await asyncio.to_thread(self._get, "/health")
            return True
        except Exception:
            return False

    async def generate(self, prompt: str, **kwargs) -> _LLMResponse:
        return await self._client.generate(
            prompt,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
        )

    async def generate_chat(self, messages: list[dict], **kwargs) -> _LLMResponse:
        return await self._client.generate_chat(
            messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
        )

    def _get(self, path: str) -> dict:
        url = f"{self.config.base_url}{path}"
        req = Request(url, method="GET")
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
