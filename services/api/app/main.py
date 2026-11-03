"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.middleware import BodySizeLimitMiddleware, RequestIDMiddleware


def configure_logging() -> None:
    """Configure structured JSON-compatible logging for the API."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # Quieten noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    configure_logging()
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="AfterMind AI",
        description="Decision-intelligence platform API",
        version="0.1.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
        # Hide internal details from error responses in production
        default_response_class=JSONResponse,
    )

    # ── Middleware stack (inner-most first) ──────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.MAX_BODY_SIZE_BYTES)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global error handler — never expose stack traces ────
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logging.getLogger("aftermind.api").error(
            "Unhandled exception request_id=%s: %s", request_id, exc, exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred",
                "code": "internal_error",
                "request_id": request_id,
            },
        )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
