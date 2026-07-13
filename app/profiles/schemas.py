from datetime import datetime

from pydantic import BaseModel

from app.common.enums import AssignmentSource, AssignmentStatus, TargetType


class ScopeTarget(BaseModel):
    target_type: TargetType
    target_id: int = 0


class ProfileCreate(BaseModel):
    name: str
    description: str | None = None
    settings: dict = {}
    created_by: int = 1


class ProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    settings: dict | None = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    version: int = 1
    settings: dict = {}
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProfileScopeResponse(BaseModel):
    profile_id: int
    scope: list[ScopeTarget]


class AssignmentResponse(BaseModel):
    id: int
    profile_id: int
    device_id: int
    source: AssignmentSource
    source_id: int | None = None
    status: AssignmentStatus
    profile_version: int
    assigned_at: datetime
    applied_at: datetime | None = None
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    status: AssignmentStatus
