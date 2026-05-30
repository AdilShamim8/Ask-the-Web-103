from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class SearchProvider(str, Enum):
    TAVILY = "tavily"
    SERPAPI = "serpapi"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM
    openai_api_key: SecretStr = Field(default="")
    anthropic_api_key: SecretStr = Field(default="")
    default_llm_provider: LLMProvider = LLMProvider.OPENAI
    default_model: str = "gpt-4o"
    fallback_model: str = "gpt-4o-mini"

    # Search
    tavily_api_key: SecretStr = Field(default="")
    serpapi_api_key: SecretStr = Field(default="")
    search_provider: SearchProvider = SearchProvider.TAVILY

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    app_env: Literal["development", "staging", "production"] = "production"
    log_level: str = "INFO"
    max_agent_iterations: int = 10
    max_tokens_per_response: int = 4096
    context_window_limit: int = 120000

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Timeouts
    llm_timeout: float = 60.0
    search_timeout: float = 15.0
    scrape_timeout: float = 20.0

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()