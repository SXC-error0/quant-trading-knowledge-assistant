from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed service configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Quant Trading Knowledge Assistant"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_v1_prefix: str = "/api/v1"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "quant_trading_knowledge"

    embedding_base_url: str = "https://your-provider.example/v1"
    embedding_api_key: str = "replace_with_your_embedding_key"
    embedding_model: str = "your-embedding-model"
    embedding_dimensions: int = Field(default=1024, ge=1)

    llm_base_url: str = "https://your-provider.example/v1"
    llm_api_key: str = "replace_with_your_llm_key"
    llm_model: str = "your-chat-model"
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    retrieval_candidate_k: int = Field(default=20, ge=1, le=100)
    retrieval_default_top_k: int = Field(default=5, ge=1, le=20)

    @staticmethod
    def _configured(key: str, model: str) -> bool:
        return "replace_with" not in key and not model.startswith("your-")

    def embedding_configuration_ready(self) -> bool:
        return self._configured(self.embedding_api_key, self.embedding_model)

    def llm_configuration_ready(self) -> bool:
        return self._configured(self.llm_api_key, self.llm_model)

    def model_configuration_ready(self) -> bool:
        return self.embedding_configuration_ready() and self.llm_configuration_ready()


@lru_cache
def get_settings() -> Settings:
    return Settings()
