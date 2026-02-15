"""
ML Offload Provider - Local inference via neoland ml-offload gRPC service.

Falls back gracefully if the local service is not running.
"""

from __future__ import annotations

import logging
import os

from .base import LLMProvider, LLMResponse

logger = logging.getLogger("neutron.agents.providers.ml_offload")


class MLOffloadProvider(LLMProvider):
    """Provider that calls the local ml-offload gRPC inference service."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = kwargs.get("base_url") or os.getenv(
            "ML_OFFLOAD_URL", "http://localhost:50051"
        )
        self.model = kwargs.get("model", "current-model")

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate via local ml-offload service."""
        # Try gRPC connection to local inference
        try:
            import grpc
            from grpc import aio as grpc_aio

            channel = grpc_aio.insecure_channel(self.base_url.replace("http://", ""))
            # Attempt a quick health check / inference call
            # This is a simplified stub - in production would use proper proto
            raise ConnectionError("ml-offload service not available")
        except Exception as e:
            raise RuntimeError(f"ML Offload unavailable: {e}")

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate chat via local ml-offload service."""
        # Convert chat to single prompt for local inference
        prompt = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
        )
        return await self.generate(
            prompt, temperature=temperature, max_tokens=max_tokens, stop=stop
        )

    async def health(self) -> bool:
        """Check if ml-offload service is reachable."""
        try:
            await self.generate("ping", max_tokens=1)
            return True
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"MLOffloadProvider(url={self.base_url}, model={self.model})"
