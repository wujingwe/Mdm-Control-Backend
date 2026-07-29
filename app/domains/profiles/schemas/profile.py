from datetime import datetime


from app.infra.common.enums import AssignmentDesiredState, AssignmentStatus
from app.infra.common.schemas import CamelModel, Scope
from app.domains.profiles.schemas.policy import Policy


class ProfileCreate(CamelModel):
    name: str
    description: str | None = None
    policy: Policy
    scope: Scope


class ProfileUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    policy: Policy | None = None
    scope: Scope | None = None


class ProfileResponse(CamelModel):
    id: int
    name: str
    description: str | None = None
    version: int
    policy: Policy
    scope: Scope
    created_by: int
    created_at: datetime
    updated_at: datetime


class AssignmentResponse(CamelModel):
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


class StatusUpdate(CamelModel):
    status: AssignmentStatus


class AssignmentUpsert(CamelModel):
    profile_id: int
    device_id: int
    status: AssignmentStatus
    desired_state: AssignmentDesiredState = AssignmentDesiredState.PRESENT
    profile_version: int
    applied_at: datetime | None = None
    revoked_at: datetime | None = None
