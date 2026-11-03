"""Authentication service — registration, login, token refresh, workspace provisioning."""

from __future__ import annotations

import jwt
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.subscription import Subscription
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.user_repo import UserRepo
from app.repositories.workspace_repo import WorkspaceRepo
from app.schemas.auth import TokenResponse, UserRegister


def _slugify(text: str) -> str:
    """Create a URL-safe slug from text."""
    return text.lower().strip().replace(" ", "-")[:50]


def _unique_slug(repo: WorkspaceRepo, base: str) -> str:
    """Ensure slug uniqueness by appending a short suffix if needed."""
    slug = base
    suffix = 1
    while repo.get_by_slug(slug) is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


class AuthService:
    """Handles authentication flows and personal workspace provisioning."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepo(db)
        self.workspace_repo = WorkspaceRepo(db)

    def register(self, payload: UserRegister) -> tuple[str, str]:
        """Register a new user and create their personal workspace.

        Returns (user_id, access_token) on success.
        Raises HTTPException on duplicate email.
        """
        existing = self.user_repo.get_by_email(payload.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        user = self.user_repo.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )

        # Provision a personal workspace
        slug = _unique_slug(
            self.workspace_repo,
            _slugify(payload.full_name or payload.email.split("@")[0]) + "-workspace",
        )
        workspace = self.workspace_repo.create(
            name=(payload.full_name or payload.email.split("@")[0]) + "'s Workspace",
            slug=slug,
            owner_id=user.id,
        )
        self.workspace_repo.add_member(workspace.id, user.id, role="owner")

        # Provision a free subscription
        self.db.add(Subscription(workspace_id=workspace.id, tier="free", status="active"))

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration failed due to a conflict",
            ) from None

        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        return access, refresh

    def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate a user and return token pair."""
        user = self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=15 * 60,
        )

    def refresh(self, refresh_token: str) -> TokenResponse:
        """Verify a refresh token and issue a new access token."""
        try:
            payload = decode_token(refresh_token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            ) from None
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            ) from None

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        user = self.user_repo.get_by_id(user_id) if user_id else None
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        access = create_access_token(user.id)
        new_refresh = create_refresh_token(user.id)
        return TokenResponse(
            access_token=access,
            refresh_token=new_refresh,
            expires_in=15 * 60,
        )
