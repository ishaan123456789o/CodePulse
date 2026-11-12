import time
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.routes import router
from app.core.config import get_settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger()
app = FastAPI(
    title="CodePulse API",
    version="0.1.0",
    description="Observed open-source momentum. Anonymous workspace watchlists are not authenticated user accounts.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Workspace-Id"],
)
app.include_router(router)


@app.middleware("http")
async def request_log(request: Request, call_next):
    request_id = str(uuid.uuid4())
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    log.info(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.monotonic() - started) * 1000, 2),
    )
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    log.error("database_error", error_type=type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable. Please retry shortly."},
    )


@app.exception_handler(OSError)
async def connection_error(request: Request, exc: OSError):
    log.error("service_connection_error", error_type=type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "A required service is temporarily unavailable. Please retry shortly."},
    )
