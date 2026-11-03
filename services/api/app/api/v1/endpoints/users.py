"""Current user endpoints: profile view and update."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepo
from app.schemas.auth import UserProfile, UserProfileUpdate

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_me(user: User = Depends(get_current_user)) -> UserProfile:
    """Return the currently authenticated user's profile."""
    return UserProfile.model_validate(user)


@router.put("/me", response_model=UserProfile)
async def update_me(
    payload: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    """Update the current user's profile."""
    repo = UserRepo(db)
    if payload.full_name is not None:
        user.full_name = payload.full_name
    repo.update(user)
    db.commit()
    return UserProfile.model_validate(user)
