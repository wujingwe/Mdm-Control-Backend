from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.enums import AssignmentDesiredState, AssignmentStatus
from app.common.schemas import Scope
from app.profiles.schemas.policy import Policy


class ProfileCreate(BaseModel):
    name: str
    description: str | None = None
    policy: Policy
    scope: Scope
    created_by: int = 1


class ProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    policy: Policy | None = None
    scope: Scope | None = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    version: int
    policy: Policy
    scope: Scope
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentResponse(BaseModel):
    id: int
    profile_id: int
    device_id: int
    status: AssignmentStatus
    desired_state: AssignmentDesiredState
    profile_version: int
    assigned_at: datetime
    applied_at: datetime | None = None
    revoked_at: datetime | None = None
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    last_error: str | None = None
    message_id: str | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class StatusUpdate(BaseModel):
    status: AssignmentStatus


class AssignmentUpsert(BaseModel):
    profile_id: int
    device_id: int
    status: AssignmentStatus
    desired_state: AssignmentDesiredState = AssignmentDesiredState.PRESENT
    profile_version: int
    applied_at: datetime | None = None
    revoked_at: datetime | None = None
