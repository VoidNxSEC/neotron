from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    base_url: str = "http://localhost:8081"
    model: str = "default"
    temperature: float = 0.3
    max_tokens: int = 1024
    timeout: float = 30.0
    extra: dict = field(default_factory=dict)
