from typing import Literal

from pydantic import BaseModel

from app.domains.profiles.schemas.policy import Policy
from app.infra.core.types import JsonValue


class ProfilePushRequested(BaseModel):
    kind: Literal["profile.push"] = "profile.push"
    serial_number: str
    profile_id: int
    profile_config: Policy
    profile_version: int
    assignment_id: int


class ProfileRevokeRequested(BaseModel):
    kind: Literal["profile.revoke"] = "profile.revoke"
    serial_number: str
    profile_id: int
    profile_version: int
    assignment_id: int


class MobileAppPushRequested(BaseModel):
    kind: Literal["mobile_app.push"] = "mobile_app.push"
    serial_number: str
    mobile_app_id: int
    package_name: str
    package_version: str
    app_version: int
    assignment_id: int


class MobileAppRevokeRequested(BaseModel):
    kind: Literal["mobile_app.revoke"] = "mobile_app.revoke"
    serial_number: str
    mobile_app_id: int
    package_name: str
    app_version: int
    assignment_id: int


class DeviceCommandRequested(BaseModel):
    kind: Literal["device.command"] = "device.command"
    serial_number: str
    command_id: int
    command_type: str
    parameters: dict[str, JsonValue]
