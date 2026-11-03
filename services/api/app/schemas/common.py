"""Shared schema components: pagination, error shapes, role enums."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PageParams(BaseModel):
    """Pagination query parameters."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: list  # populated by subclasses
    total: int
    page: int
    page_size: int


class ErrorCode(str, Enum):
    """Stable error codes for API responses."""

    AUTH_INVALID_CREDENTIALS = "auth_invalid_credentials"
    AUTH_TOKEN_EXPIRED = "auth_token_expired"
    AUTH_TOKEN_INVALID = "auth_token_invalid"
    AUTH_USER_INACTIVE = "auth_user_inactive"
    AUTH_EMAIL_EXISTS = "auth_email_exists"
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"
    VALIDATION_ERROR = "validation_error"
    CONFLICT = "conflict"
    QUOTA_EXCEEDED = "quota_exceeded"
    LLM_UNAVAILABLE = "llm_unavailable"
    SIMULATION_FAILED = "simulation_failed"
    SIMULATION_NOT_READY = "simulation_not_ready"


class ErrorResponse(BaseModel):
    """Standard error response shape."""

    detail: str
    code: str
