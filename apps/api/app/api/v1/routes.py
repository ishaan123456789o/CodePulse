from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.github.discovery import CATEGORIES
from app.models.entities import Repository
from app.repositories.catalog import list_repositories
from app.schemas.api import (
    Filters,
    HistoryOut,
    MetricsOut,
    Page,
    RepositoryOut,
    ScoreOut,
    StatusOut,
    SummaryOut,
    WatchlistIn,
    Window,
)
from app.services import catalog
from app.services.cache import cached_summary
from app.services.status import readiness, status

router = APIRouter(prefix="/api/v1")
DB = Annotated[AsyncSession, Depends(get_session)]
FilterQuery = Annotated[Filters, Query()]


def optional_workspace(x_workspace_id: Annotated[UUID | None, Header()] = None) -> str | None:
    return str(x_workspace_id) if x_workspace_id else None


def required_workspace(workspace: Annotated[str | None, Depends(optional_workspace)]) -> str:
    if workspace is None:
        raise HTTPException(400, "X-Workspace-Id UUID header is required for anonymous watchlists")
    return workspace


Workspace = Annotated[str | None, Depends(optional_workspace)]
RequiredWorkspace = Annotated[str, Depends(required_workspace)]


@router.get("/health")
async def health():
    return {"status": "ok", "service": "codepulse"}


@router.get("/health/ready")
async def ready(db: DB):
    try:
        await readiness(db)
    except Exception:
        raise HTTPException(503, "Database or Redis is unavailable") from None
    return {"status": "ready"}


@router.get("/repositories", response_model=Page)
@router.get("/search", response_model=Page)
@router.get("/discover", response_model=Page)
async def repositories(db: DB, filters: FilterQuery, workspace: Workspace):
    return await list_repositories(db, filters, workspace)


@router.get("/trending", response_model=Page)
async def trending(db: DB, filters: FilterQuery, workspace: Workspace):
    return await list_repositories(
        db, filters.model_copy(update={"score_type": "observed_momentum"}), workspace
    )


@router.get("/repositories/{repo_id}", response_model=RepositoryOut)
async def repository(repo_id: int, db: DB, workspace: Workspace, time_window: Window = "24h"):
    return await catalog.require_repository(db, repo_id, time_window, workspace)


@router.get("/repositories/{repo_id}/history", response_model=HistoryOut)
async def history(repo_id: int, db: DB, time_window: Literal["24h", "7d", "30d", "all"] = "7d"):
    return await catalog.history(db, repo_id, time_window)


@router.get("/repositories/{repo_id}/metrics", response_model=MetricsOut)
async def metrics(repo_id: int, db: DB, time_window: Window = "24h"):
    return await catalog.metrics(db, repo_id, time_window)


@router.get("/repositories/{repo_id}/score", response_model=ScoreOut | None)
async def score(repo_id: int, db: DB, time_window: Window = "24h"):
    return (await catalog.require_repository(db, repo_id, time_window)).score


@router.get("/dashboard/summary", response_model=SummaryOut)
async def summary(db: DB, time_window: Window = "24h"):
    return await cached_summary(db, time_window)


@router.get("/categories", response_model=list[str])
async def categories():
    return sorted(set(CATEGORIES.values()))


@router.get("/languages", response_model=list[str])
async def languages(db: DB):
    return (
        await db.scalars(
            select(Repository.language)
            .where(Repository.language.is_not(None))
            .distinct()
            .order_by(Repository.language)
        )
    ).all()


@router.get("/watchlist", response_model=Page)
async def watchlist(db: DB, filters: FilterQuery, workspace: RequiredWorkspace):
    return await list_repositories(db, filters, workspace, watchlist=True)


@router.post("/watchlist", status_code=201)
async def add_watchlist(body: WatchlistIn, db: DB, workspace: RequiredWorkspace):
    await catalog.add_watchlist(db, workspace, body.repository_id)
    return {"repository_id": body.repository_id, "watchlisted": True}


@router.delete("/watchlist/{repo_id}", status_code=204)
async def remove_watchlist(repo_id: int, db: DB, workspace: RequiredWorkspace):
    await catalog.remove_watchlist(db, workspace, repo_id)
    return Response(status_code=204)


@router.get("/system/status", response_model=StatusOut)
async def system_status(db: DB):
    return await status(db)
