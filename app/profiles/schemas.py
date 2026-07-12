from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class TargetType(str, Enum):
    ALL_DEVICES = "ALL_DEVICES"
    SMART_GROUP = "SMART_GROUP"
    STATIC_GROUP = "STATIC_GROUP"
    DEVICE = "DEVICE"


class AssignmentSource(str, Enum):
    DIRECT = "DIRECT"
    SMART_GROUP = "SMART_GROUP"
    STATIC_GROUP = "STATIC_GROUP"
    ALL_DEVICES = "ALL_DEVICES"


class AssignmentStatus(str, Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"
    REMOVED = "REMOVED"


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
