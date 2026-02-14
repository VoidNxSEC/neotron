from .base import LLMProvider, LLMResponse, ProviderConfig
from .llamacpp import LlamaCppProvider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ProviderConfig",
    "LlamaCppProvider",
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
    }

    # Lazy imports for optional providers
    if provider_type == "openai":
        from .openai_provider import OpenAIProvider
        providers["openai"] = OpenAIProvider
    elif provider_type == "anthropic":
        from .anthropic_provider import AnthropicProvider
        providers["anthropic"] = AnthropicProvider
    elif provider_type == "deepseek":
        from .openai_provider import OpenAIProvider
        # DeepSeek uses OpenAI-compatible API
        if "base_url" not in kwargs:
            kwargs["base_url"] = "https://api.deepseek.com/v1"
        providers["deepseek"] = OpenAIProvider

    if provider_type not in providers:
        raise ValueError(
            f"Unknown provider: {provider_type}. "
            f"Available: {list(providers.keys())}"
        )

    return providers[provider_type](**kwargs)
