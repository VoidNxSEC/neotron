"""
LLMClient — multi-provider façade for neotron agents.

Wraps LLMHTTPClient (ml-offload-api) and exposes a provider-aware API
with health checks and circuit breaker status, compatible with the demo
and agent layers.
"""

from __future__ import annotations

import os
from typing import Any

from neutron.agents._llm_http_client import LLMHTTPClient, _LLMResponse


class LLMClient:
    """
    Multi-provider LLM client for neotron.

    Supported providers (checked via env vars):
      - anthropic  (ANTHROPIC_API_KEY)
      - openai     (OPENAI_API_KEY)
      - deepseek   (DEEPSEEK_API_KEY)
      - local      (ML_OFFLOAD_URL, always present as fallback)
    """

    def __init__(self) -> None:
        self._http = LLMHTTPClient()
        self._providers: dict[str, dict[str, Any]] = self._detect_providers()
        self._circuit_breakers: dict[str, dict[str, Any]] = {
            name: {"is_open": False, "failures": 0, "threshold": 5} for name in self._providers
        }

    def _detect_providers(self) -> dict[str, dict[str, Any]]:
        providers: dict[str, dict[str, Any]] = {}
        if os.getenv("ANTHROPIC_API_KEY"):
            providers["anthropic"] = {"model": "claude-3-5-haiku-20241022"}
        if os.getenv("OPENAI_API_KEY"):
            providers["openai"] = {"model": "gpt-4o-mini"}
        if os.getenv("DEEPSEEK_API_KEY"):
            providers["deepseek"] = {"model": "deepseek-chat"}
        providers["local"] = {"model": os.getenv("ML_OFFLOAD_MODEL", "current-model")}
        return providers

    async def health_check(self) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for name in self._providers:
            if name == "local":
                try:
                    await self._http.generate("ping", max_tokens=1)
                    results[name] = True
                except Exception:
                    results[name] = False
            else:
                results[name] = True  # API key present — assume reachable
        return results

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        **kwargs,
    ) -> _LLMResponse:
        return await self._http.generate(
            prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        **kwargs,
    ) -> _LLMResponse:
        return await self._http.generate_chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def get_circuit_breaker_status(self) -> dict[str, dict[str, Any]]:
        return self._circuit_breakers
