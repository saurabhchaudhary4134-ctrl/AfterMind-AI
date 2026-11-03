"""Workspace and workspace-member schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class WorkspaceBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    owner_id: str
    my_role: str | None = None
    created_at: datetime


class WorkspaceMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    user_id: str
    role: str
    created_at: datetime


class AddMember(BaseModel):
    user_id: str
    role: WorkspaceRole = WorkspaceRole.MEMBER


class UpdateMemberRole(BaseModel):
    role: WorkspaceRole
