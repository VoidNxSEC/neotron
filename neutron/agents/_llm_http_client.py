"""
LLM HTTP Client stub for neotron.

Used when mlops package is not installed.
Delegates to ml-offload-api REST endpoint (OpenAI-compatible /v1/chat/completions).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger("neutron.agents.llm_http_client")

ML_OFFLOAD_URL = os.getenv("ML_OFFLOAD_URL", "http://localhost:8080")


@dataclass
class _LLMResponse:
    """Minimal response compatible with LLMClient.generate() callers."""

    content: str
    model: str = ""
    finish_reason: str = "stop"
    total_tokens: int = 0
    raw: dict = field(default_factory=dict)


class LLMHTTPClient:
    """
    Minimal LLM client that calls ml-offload-api REST endpoint.

    Drop-in replacement for mlops.llm.client.LLMClient for neotron.
    Requires ml-offload-api running at ML_OFFLOAD_URL (default: localhost:8080).
    """

    def __init__(self, config=None):
        self.base_url = ML_OFFLOAD_URL
        self._model = os.getenv("ML_OFFLOAD_MODEL", "current-model")

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs,
    ) -> _LLMResponse:
        """Generate via ml-offload-api /v1/chat/completions."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return await self.generate_chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
        )

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs,
    ) -> _LLMResponse:
        """Generate from chat messages via ml-offload-api."""
        import asyncio

        body: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature if temperature is not None else 0.3,
            "max_tokens": max_tokens or 1024,
        }
        if stop:
            body["stop"] = stop

        try:
            raw = await asyncio.to_thread(self._post, "/v1/chat/completions", body)
            choice = raw.get("choices", [{}])[0]
            message = choice.get("message", {})
            usage = raw.get("usage", {})

            return _LLMResponse(
                content=message.get("content", "").strip(),
                model=raw.get("model", self._model),
                finish_reason=choice.get("finish_reason", "stop"),
                total_tokens=usage.get("total_tokens", 0),
                raw=raw,
            )
        except Exception as e:
            raise RuntimeError(
                f"ml-offload-api call failed ({self.base_url}): {e}. "
                "Ensure ml-offload-api is running or install mlops package."
            )

    def _post(self, path: str, body: dict) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8")
        req = Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_circuit_breaker_status(self) -> dict:
        return {}
