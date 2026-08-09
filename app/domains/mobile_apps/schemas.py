from datetime import datetime

from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.shared.scope import Scope
from app.infra.common.schemas import CamelModel


class MobileAppResponse(CamelModel):
    id: int
    name: str
    enabled: bool
    package_version: str
    package_name: str
    version: int
    scope: Scope
    created_by: int
    created_at: datetime
    updated_at: datetime


class MobileAppCreate(CamelModel):
    name: str
    enabled: bool
    package_version: str
    package_name: str
    scope: Scope


class MobileAppUpdate(CamelModel):
    name: str | None = None
    enabled: bool | None = None
    package_version: str | None = None
    scope: Scope | None = None


class MobileAppAssignmentResponse(CamelModel):
    id: int
    mobile_app_id: int
    device_id: int
    status: AssignmentStatus
    desired_state: AssignmentDesiredState
    version: int
    assigned_at: datetime
    applied_at: datetime | None = None
    revoked_at: datetime | None = None
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    last_error: str | None = None
    message_id: str | None = None
    updated_at: datetime


class MobileAppStatusUpdate(CamelModel):
    status: AssignmentStatus


class MobileAppAssignmentReportIn(CamelModel):
    assignment_id: int
    status: AssignmentStatus
    result_message: str | None = None


class MobileAppAssignmentUpsert(CamelModel):
    mobile_app_id: int
    device_id: int
    status: AssignmentStatus
    desired_state: AssignmentDesiredState = AssignmentDesiredState.PRESENT
    version: int | None = None
    applied_at: datetime | None = None
    revoked_at: datetime | None = None
