"""Workspace endpoints: list, create, get, members management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepo
from app.repositories.workspace_repo import WorkspaceRepo
from app.schemas.workspace import (
    AddMember,
    UpdateMemberRole,
    WorkspaceCreate,
    WorkspaceMemberOut,
    WorkspaceOut,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _slugify(text: str) -> str:
    return text.lower().strip().replace(" ", "-")[:50]


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all workspaces the current user belongs to."""
    repo = WorkspaceRepo(db)
    workspaces = repo.list_for_user(user.id)
    result = []
    for ws in workspaces:
        membership = repo.get_membership(ws.id, user.id)
        result.append(
            WorkspaceOut(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
                owner_id=ws.owner_id,
                my_role=membership.role if membership else None,
                created_at=ws.created_at,
            )
        )
    return result


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new workspace. The creator becomes the owner."""
    repo = WorkspaceRepo(db)
    slug = payload.slug or _slugify(payload.name)
    if repo.get_by_slug(slug):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already taken")
    ws = repo.create(name=payload.name, slug=slug, owner_id=user.id)
    repo.add_member(ws.id, user.id, role="owner")
    db.commit()
    return WorkspaceOut(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        owner_id=ws.owner_id,
        my_role="owner",
        created_at=ws.created_at,
    )


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a workspace. The caller must be a member."""
    repo = WorkspaceRepo(db)
    ws = repo.get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    membership = repo.get_membership(workspace_id, user.id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    return WorkspaceOut(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        owner_id=ws.owner_id,
        my_role=membership.role,
        created_at=ws.created_at,
    )


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberOut])
async def list_members(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List members of a workspace. The caller must be a member."""
    repo = WorkspaceRepo(db)
    ws = repo.get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if repo.get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    return repo.list_members(workspace_id)


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    workspace_id: str,
    payload: AddMember,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a user to the workspace. Only owners/admins can do this."""
    repo = WorkspaceRepo(db)
    ws = repo.get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    caller_membership = repo.get_membership(workspace_id, user.id)
    if caller_membership is None or caller_membership.role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    target_user = UserRepo(db).get_by_id(payload.user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if repo.get_membership(workspace_id, payload.user_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already a member")

    member = repo.add_member(workspace_id, payload.user_id, role=payload.role.value)
    db.commit()
    return member


@router.patch("/{workspace_id}/members/{member_user_id}", response_model=WorkspaceMemberOut)
async def update_member_role(
    workspace_id: str,
    member_user_id: str,
    payload: UpdateMemberRole,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a member's role. Only owners/admins can do this."""
    repo = WorkspaceRepo(db)
    ws = repo.get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    caller_membership = repo.get_membership(workspace_id, user.id)
    if caller_membership is None or caller_membership.role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    member = repo.get_membership(workspace_id, member_user_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if member.role == "owner" and payload.role != "owner":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change owner role")

    member = repo.update_member_role(member, payload.role.value)
    db.commit()
    return member


@router.delete("/{workspace_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: str,
    member_user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a member from the workspace."""
    repo = WorkspaceRepo(db)
    ws = repo.get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    caller_membership = repo.get_membership(workspace_id, user.id)
    if caller_membership is None or caller_membership.role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    member = repo.get_membership(workspace_id, member_user_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if member.role == "owner":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove owner")

    repo.remove_member(member)
    db.commit()


@router.get("/{workspace_id}/usage")
async def get_workspace_usage(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return quota usage for a workspace."""
    from app.core.quotas import get_usage_summary

    ws = WorkspaceRepo(db).get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    return get_usage_summary(db, workspace_id)


@router.get("/{workspace_id}/subscription")
async def get_workspace_subscription(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return subscription details for a workspace."""
    from sqlalchemy import select as _select
    from app.models.subscription import Subscription

    ws = WorkspaceRepo(db).get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")

    sub = db.execute(
        _select(Subscription).where(Subscription.workspace_id == workspace_id)
    ).scalar_one_or_none()

    if sub is None:
        return {"tier": "free", "status": "active", "workspace_id": workspace_id}
    return {
        "id": sub.id,
        "workspace_id": sub.workspace_id,
        "tier": sub.tier,
        "status": sub.status,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "created_at": sub.created_at.isoformat(),
    }
