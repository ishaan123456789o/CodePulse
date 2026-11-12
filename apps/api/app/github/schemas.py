from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GitHubOwner(BaseModel):
    login: str = Field(min_length=1)


class GitHubRepository(BaseModel):
    """Validate external responses before mutating the source of truth."""

    model_config = ConfigDict(extra="ignore")
    id: int = Field(gt=0)
    owner: GitHubOwner
    name: str = Field(min_length=1)
    full_name: str = Field(min_length=3)
    created_at: datetime
    pushed_at: datetime | None = None
    updated_at: datetime | None = None
    description: str | None = None
    language: str | None = None
    topics: list[str] = []
    stargazers_count: int = Field(ge=0)
    forks_count: int = Field(ge=0)
    open_issues_count: int = Field(ge=0)
    default_branch: str = "main"
    license: dict[str, Any] | None = None
    size: int | None = None
    archived: bool = False
    disabled: bool = False
    private: bool = False
    visibility: str = "public"
