from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")
    database_url: str = "postgresql+asyncpg://codepulse:codepulse-local@localhost:5432/codepulse"
    redis_url: str = "redis://localhost:6379/0"
    github_token: SecretStr = SecretStr("")
    cors_origins: list[str] = ["http://localhost:3000"]
    demo_mode: bool = False
    optional_activity_enabled: bool = False
    summary_cache_seconds: int = Field(30, ge=0, le=300)
    discovery_languages: list[str] = []
    discovery_extra_queries: list[str] = []
    discovery_request_budget: int = Field(10, ge=1, le=100)
    tracking_request_budget: int = Field(60, ge=1, le=1000)
    discovery_interval_seconds: int = Field(21600, ge=3600)
    track_high_hours: int = Field(1, ge=1)
    track_normal_hours: int = Field(6, ge=1)
    track_low_hours: int = Field(24, ge=1)
    github_min_interval_seconds: float = Field(2, ge=1)
    discovery_topics: list[str] = [
        "machine-learning",
        "ai-agents",
        "developer-tools",
        "database",
        "distributed-systems",
        "security",
        "web",
        "data-engineering",
        "programming-language",
        "open-source",
    ]

    @model_validator(mode="after")
    def isolate_demo(self):
        if self.demo_mode and "demo" not in self.database_url.rsplit("/", 1)[-1]:
            raise ValueError("DEMO_MODE requires a separate database whose name contains 'demo'")
        return self

    @property
    def github_configured(self) -> bool:
        return bool(self.github_token.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
