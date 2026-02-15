from .base import LLMProvider, LLMResponse, ProviderConfig
from .llamacpp import LlamaCppProvider
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider, DeepSeekProvider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ProviderConfig",
    "LlamaCppProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "DeepSeekProvider",
    "create_provider",
]


def create_provider(
    provider_type: str = "llamacpp",
    **kwargs,
) -> LLMProvider:
    """Factory to create LLM providers.

    Args:
        provider_type: One of "llamacpp", "openai", "anthropic", "deepseek"
        **kwargs: Passed to provider constructor

    Returns:
        LLMProvider instance
    """
    providers = {
        "llamacpp": LlamaCppProvider,
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "deepseek": DeepSeekProvider,
    }

    if provider_type not in providers:
        raise ValueError(
            f"Unknown provider: {provider_type}. "
            f"Available: {list(providers.keys())}"
        )

    return providers[provider_type](**kwargs)
