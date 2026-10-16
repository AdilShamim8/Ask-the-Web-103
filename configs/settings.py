"""
Application settings — single source of configuration truth.

Production rules:
* Secrets are ``SecretStr``; the redaction processor in logging_config
  guarantees they never render in logs.
* Lists arrive as comma-separated env strings and are parsed here, so
  ops can write ``LLM_PROVIDER_ORDER=openai,anthropic`` without JSON.
* ``app_env`` defaults to ``development`` — production must opt in
  explicitly. (The old default of "production" silently disabled docs and
  JSON logs in local runs; safe defaults beat convenient ones.)
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class SearchProvider(StrEnum):
    TAVILY = "tavily"
    SERPAPI = "serpapi"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────
    openai_api_key: SecretStr = Field(default="")
    anthropic_api_key: SecretStr = Field(default="")
    default_llm_provider: LLMProvider = LLMProvider.OPENAI
    default_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"          # cheap tier: routing, tool selection
    fallback_model: str = "gpt-4o-mini"
    llm_provider_order_str: str = "openai,anthropic"  # ADR-002 fallback chain

    # ── Search (ADR-002: ordered fallback, not single choice) ───────────
    tavily_api_key: SecretStr = Field(default="")
    serpapi_api_key: SecretStr = Field(default="")
    search_provider: SearchProvider = SearchProvider.TAVILY
    search_provider_order_str: str = "tavily,serpapi"

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── App ──────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_version: str = "2.0.0"
    max_agent_iterations: int = 10
    max_tokens_per_response: int = 4096
    context_window_limit: int = 120_000

    # ── Budgets (ADR-005) ────────────────────────────────────────────────
    budget_max_input_tokens: int = 120_000
    budget_max_output_tokens: int = 16_000
    budget_max_tool_calls: int = 25
    budget_max_steps: int = 12
    budget_deadline_s: float = 45.0

    # ── Rate limiting ────────────────────────────────────────────────────
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    rate_limit_per_user_requests: int = 30

    # ── Timeouts ─────────────────────────────────────────────────────────
    llm_timeout: float = 60.0
    search_timeout: float = 15.0
    scrape_timeout: float = 20.0
    tool_timeout_s: float = 15.0

    # ── Tool safety (FMEA FM-08 / FM-09) ────────────────────────────────
    max_response_bytes: int = 3_000_000          # fetch body cap (3 MB)
    max_tool_result_chars: int = 8_000           # result truncation before context
    max_parallel_tool_calls: int = 5

    # ── Cache (ADR-003) ─────────────────────────────────────────────────
    cache_ttl_s: int = 3_600
    cache_stale_s: int = 600                     # SWR window after soft expiry
    cache_jitter_ratio: float = 0.3              # ±30% TTL jitter
    cache_lock_ttl_ms: int = 8_000               # singleflight lock TTL
    cache_wait_ms: int = 5_000                   # follower wait budget

    # ── HTTP pool (tools/http_client.py) ─────────────────────────────────
    http_pool_max_connections: int = 100
    http_pool_max_keepalive: int = 20

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v.upper()

    # ── Derived (comma-separated env lists → enums) ──────────────────────

    @property
    def llm_provider_order(self) -> list[LLMProvider]:
        return [
            p for p in (
                LLMProvider(x.strip())
                for x in self.llm_provider_order_str.split(",")
                if x.strip()
            )
            if self._has_llm_key(p)
        ] or [self.default_llm_provider]

    @property
    def search_provider_order(self) -> list[SearchProvider]:
        return [
            p for p in (
                SearchProvider(x.strip())
                for x in self.search_provider_order_str.split(",")
                if x.strip()
            )
            if self._has_search_key(p)
        ] or [self.search_provider]

    def _has_llm_key(self, provider: LLMProvider) -> bool:
        key = (
            self.openai_api_key if provider == LLMProvider.OPENAI
            else self.anthropic_api_key
        )
        return bool(key.get_secret_value())

    def _has_search_key(self, provider: SearchProvider) -> bool:
        key = (
            self.tavily_api_key if provider == SearchProvider.TAVILY
            else self.serpapi_api_key
        )
        return bool(key.get_secret_value())

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
