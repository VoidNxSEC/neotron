from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # NVIDIA NIM Hub
    nvidia_api_key: str | None = None
    nvidia_model: str = "meta/llama3-8b-instruct"

    # Llama.cpp (via OpenAI-compatible API)
    llama_cpp_base_url: str = "http://localhost:8081/v1"
    llama_cpp_model: str = "local-model"

    # Default Provider choice ("nvidia" or "llamacpp")
    llm_provider: str = "nvidia"

    # Storage
    chroma_db_dir: str = "./.langmath_brain"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="LANGMATH_", extra="ignore")


settings = Settings()
