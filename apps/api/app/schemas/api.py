from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Window = Literal["24h", "7d", "30d"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ScoreOut(ORMModel):
    score: float
    score_type: str
    scoring_version: str
    time_window: str
    calculated_at: datetime
    confidence: float
    coverage: dict[str, Any]
    feature_breakdown: dict[str, Any]
    explanation: list[str]
    stale: bool = False


class SnapshotOut(ORMModel):
    observed_at: datetime
    stars: int
    forks: int
    open_issues: int
    contributors: int | None
    commits_7d: int | None
    collection_source: str


class RepositoryOut(ORMModel):
    id: int
    github_id: int
    owner: str
    name: str
    full_name: str
    url: str
    description: str | None
    language: str | None
    topics: list[str]
    category: str
    stars: int
    forks: int
    open_issues: int
    default_branch: str
    license: str | None
    size: int | None
    archived: bool
    disabled: bool
    contributors: int | None
    commits_7d: int | None
    activity_fetched_at: datetime | None
    created_at_github: datetime
    pushed_at: datetime | None
    updated_at_github: datetime | None
    discovered_at: datetime
    last_fetched_at: datetime | None
    tracking_priority: str
    score: ScoreOut | None = None
    score_change: float | None = None
    sparkline: list[SnapshotOut] = []
    watchlisted: bool = False


class Page(BaseModel):
    items: list[RepositoryOut]
    total: int
    page: int
    page_size: int
    demo: bool


class Filters(BaseModel):
    q: str = Field("", max_length=200)
    language: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=100)
    min_stars: int = Field(0, ge=0)
    max_stars: int | None = Field(None, ge=0)
    min_score: float = Field(0, ge=0, le=100)
    score_type: Literal["observed_momentum", "early_discovery"] | None = None
    emerging: bool = False
    new_only: bool = False
    time_window: Window = "24h"
    sort: Literal["momentum", "stars", "growth", "newest", "name"] = "momentum"
    page: int = Field(1, ge=1, le=10000)
    page_size: int = Field(20, ge=1, le=100)

    @model_validator(mode="after")
    def valid_range(self):
        if self.max_stars is not None and self.max_stars < self.min_stars:
            raise ValueError("Maximum stars must be greater than or equal to minimum stars")
        return self


class WatchlistIn(BaseModel):
    repository_id: int = Field(gt=0)


class HistoryOut(BaseModel):
    repository_id: int
    time_window: str
    observations: list[SnapshotOut]
    demo: bool


class MetricsOut(BaseModel):
    repository_id: int
    time_window: Window
    features: dict[str, float | None]
    coverage: dict[str, Any]
    peers: list[RepositoryOut]


class SummaryOut(BaseModel):
    repositories_tracked: int
    emerging_repositories: int
    high_momentum_repositories: int
    new_discoveries_today: int
    last_observation_at: datetime | None
    categories: list[dict[str, Any]]
    momentum_distribution: list[dict[str, Any]]
    fastest_growing: list[RepositoryOut]
    recently_discovered: list[RepositoryOut]
    demo: bool


class StatusOut(BaseModel):
    ingestion: str
    github_configured: bool
    demo: bool
    redis: str
    worker_last_seen: float | None
    worker_healthy: bool
    cooldown_until: float | None
    quotas: dict[str, Any]
    tasks: dict[str, Any]
    last_discovery: dict[str, Any] | None
    recent_failures: int
    cadences_hours: dict[str, int]
    budgets: dict[str, int]
