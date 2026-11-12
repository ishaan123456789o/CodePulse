from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    cast,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


json_type = JSON().with_variant(JSONB, "postgresql")


class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    owner: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(310), index=True)
    url: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(100), index=True)
    topics: Mapped[list[str]] = mapped_column(json_type, default=list)
    category: Mapped[str] = mapped_column(String(100), index=True, default="General Open Source")
    created_at_github: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at_github: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stars: Mapped[int] = mapped_column(Integer, index=True)
    forks: Mapped[int] = mapped_column(Integer)
    open_issues: Mapped[int] = mapped_column(Integer)
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    license: Mapped[str | None] = mapped_column(String(100))
    size: Mapped[int | None] = mapped_column(Integer)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    contributors: Mapped[int | None] = mapped_column(Integer)
    commits_7d: Mapped[int | None] = mapped_column(Integer)
    activity_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_fetch_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    tracking_priority: Mapped[str] = mapped_column(String(20), default="normal")
    etag: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Snapshot(Base):
    __tablename__ = "repository_snapshots"
    __table_args__ = (
        UniqueConstraint("repository_id", "observation_bucket"),
        Index("ix_snapshot_repo_time", "repository_id", "observed_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observation_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stars: Mapped[int] = mapped_column(Integer)
    forks: Mapped[int] = mapped_column(Integer)
    open_issues: Mapped[int] = mapped_column(Integer)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contributors: Mapped[int | None] = mapped_column(Integer)
    commits_7d: Mapped[int | None] = mapped_column(Integer)
    collection_source: Mapped[str] = mapped_column(String(40), default="github_rest")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Score(Base):
    __tablename__ = "repository_scores"
    __table_args__ = (
        UniqueConstraint("repository_id", "time_window", "calculated_at", "scoring_version"),
        Index("ix_score_repo_window_time", "repository_id", "time_window", "calculated_at"),
        Index("ix_score_ranking", "time_window", "score"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    score_type: Mapped[str] = mapped_column(String(30))
    scoring_version: Mapped[str] = mapped_column(String(30))
    time_window: Mapped[str] = mapped_column(String(10))
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    coverage: Mapped[dict[str, Any]] = mapped_column(json_type)
    feature_breakdown: Mapped[dict[str, Any]] = mapped_column(json_type)
    explanation: Mapped[list[str]] = mapped_column(json_type)


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40), default="github_search")
    query: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    repositories_found: Mapped[int] = mapped_column(Integer, default=0)
    repositories_inserted: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(30))
    repository_id: Mapped[int | None] = mapped_column(
        ForeignKey("repositories.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    __table_args__ = (
        UniqueConstraint("workspace_id", "repository_id"),
        Index("ix_watchlist_workspace", "workspace_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36))
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# PostgreSQL-only expression indexes; excluded from SQLite fixture DDL.

Index(
    "ix_repositories_search",
    text(
        "to_tsvector('simple'::regconfig, (COALESCE(name, ''::character varying)::text || ' '::text) || COALESCE(description, ''::text))"
    ),
    postgresql_using="gin",
    _table=Repository.__table__,
).ddl_if(dialect="postgresql")
Index(
    "ix_repositories_name_prefix",
    func.lower(cast(Repository.full_name, Text)).label("full_name_lower"),
    postgresql_ops={"full_name_lower": "text_pattern_ops"},
    _table=Repository.__table__,
).ddl_if(dialect="postgresql")

Index(
    "ix_repositories_short_name_prefix",
    func.lower(cast(Repository.name, Text)).label("name_lower"),
    postgresql_ops={"name_lower": "text_pattern_ops"},
).ddl_if(dialect="postgresql")


class Forecast(Base):
    __tablename__ = "repository_forecasts"
    __table_args__ = (
        UniqueConstraint("repository_id", "forecast_day", "model_version"),
        Index("ix_forecast_repo_issued", "repository_id", "issued_at"),
        Index("ix_forecast_due", "target_at", "evaluated_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    forecast_day: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    target_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    model_version: Mapped[str] = mapped_column(String(30))
    demo: Mapped[bool] = mapped_column(Boolean)
    stars_at_origin: Mapped[int] = mapped_column(Integer)
    projected_growth: Mapped[float] = mapped_column(Float)
    baseline_growth: Mapped[float] = mapped_column(Float)
    breakout_threshold: Mapped[int] = mapped_column(Integer)
    breakout_ratio: Mapped[float] = mapped_column(Float)
    predicted_breakout: Mapped[bool] = mapped_column(Boolean)
    features: Mapped[dict[str, Any]] = mapped_column(json_type)
    explanation: Mapped[list[str]] = mapped_column(json_type)
    realized_growth: Mapped[float | None] = mapped_column(Float)
    actual_breakout: Mapped[bool | None] = mapped_column(Boolean)
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evaluation_status: Mapped[str] = mapped_column(String(30), default="pending")
