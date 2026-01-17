"""
DSPy Adapter for Multi-Provider LLM Integration

Connects DSPy framework to existing provider infrastructure (SecureLLM, Phantom).
Phase 1 MVP: Simple adapter for quick validation.
"""

import dspy
from typing import Optional, Dict, Any, List
import requests
import os


class SimpleLLMProvider:
    """
    Simple LLM provider for MVP testing.
    Can be replaced with Phantom/SecureLLM integration later.
    """

    def __init__(self, provider_name: str, api_key: Optional[str] = None):
        self.provider_name = provider_name
        self.api_key = api_key or os.getenv(f"{provider_name.upper()}_API_KEY")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> str:
        """
        Generate text from prompt.
        MVP: Simple implementation, can be enhanced with SecureLLM later.
        """
        if self.provider_name == "deepseek":
            return self._call_deepseek(prompt, temperature, max_tokens)
        elif self.provider_name == "openai":
            return self._call_openai(prompt, temperature, max_tokens)
        elif self.provider_name == "local":
            return self._call_local(prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {self.provider_name}")

    def _call_deepseek(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Call DeepSeek API"""
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"DeepSeek call failed: {e}")

    def _call_openai(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Call OpenAI API"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective for testing
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI call failed: {e}")

    def _call_local(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Call local llama.cpp server (OpenAI-compatible API)"""
        try:
            # llama.cpp server expõe API compatível com OpenAI
            # Porta padrão: 8080
            # Verifique sua porta com: ps aux | grep llama-server
            import openai

            client = openai.OpenAI(
                api_key="not-needed",  # llama.cpp não precisa de key
                base_url="http://localhost:8080/v1"  # API compatível com OpenAI
            )

            response = client.chat.completions.create(
                model="local-model",  # Nome do modelo carregado no llama.cpp
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"Local llama.cpp call failed: {e}. "
                             f"Certifique-se que llama.cpp server está rodando em localhost:8080")


class DSPyProviderAdapter(dspy.LM):
    """
    Adapter to use LLM providers with DSPy.

    Usage:
        provider = DSPyProviderAdapter("deepseek")
        dspy.configure(lm=provider)
    """

    def __init__(self, provider_name: str, api_key: Optional[str] = None):
        super().__init__(model=provider_name)
        self.provider = SimpleLLMProvider(provider_name, api_key)
        self.provider_name = provider_name
        self.history = []

    def basic_request(self, prompt: str, **kwargs) -> str:
        """
        DSPy calls this method for text generation.

        Args:
            prompt: The prompt string
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text
        """
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 512)

        try:
            response = self.provider.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Track history for debugging
            self.history.append({
                "prompt": prompt,
                "response": response,
                "provider": self.provider_name,
                "kwargs": kwargs
            })

            return response

        except Exception as e:
            error_msg = f"Provider {self.provider_name} failed: {e}"
            print(f"⚠️  {error_msg}")
            raise

    def __call__(self, prompt: str, **kwargs) -> List[str]:
        """
        Alternative calling interface for DSPy.
        Returns list of completions (we return single completion for simplicity).
        """
        response = self.basic_request(prompt, **kwargs)
        return [response]

    def get_history(self) -> List[Dict[str, Any]]:
        """Get generation history for debugging/analysis"""
        return self.history

    def clear_history(self):
        """Clear generation history"""
        self.history = []


# Convenience functions for quick setup

def configure_deepseek(api_key: Optional[str] = None):
    """Configure DSPy to use DeepSeek"""
    adapter = DSPyProviderAdapter("deepseek", api_key)
    dspy.configure(lm=adapter)
    return adapter


def configure_openai(api_key: Optional[str] = None):
    """Configure DSPy to use OpenAI"""
    adapter = DSPyProviderAdapter("openai", api_key)
    dspy.configure(lm=adapter)
    return adapter


def configure_local():
    """Configure DSPy to use local llama.cpp server"""
    adapter = DSPyProviderAdapter("local")
    dspy.configure(lm=adapter)
    return adapter
