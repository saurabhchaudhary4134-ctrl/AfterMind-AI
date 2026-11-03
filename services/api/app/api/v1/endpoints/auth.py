"""Authentication endpoints: register, login, refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limit_auth
from app.db.session import get_db
from app.schemas.auth import RefreshRequest, TokenResponse, UserLogin, UserRegister
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    payload: UserRegister,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit_auth),
) -> TokenResponse:
    """Register a new user. Returns access + refresh tokens."""
    access, refresh = AuthService(db).register(payload)
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=15 * 60)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit_auth),
) -> TokenResponse:
    """Authenticate and return access + refresh tokens."""
    return AuthService(db).login(payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange a refresh token for a new access token."""
    return AuthService(db).refresh(payload.refresh_token)
