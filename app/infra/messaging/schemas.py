from typing import Any, Literal

from pydantic import BaseModel


class ProfilePushRequested(BaseModel):
    kind: Literal["profile.push"] = "profile.push"
    serial_number: str
    profile_id: int
    profile_config: dict[str, Any]
    profile_version: int | None = None
    assignment_id: int | None = None


class ProfileRevokeRequested(BaseModel):
    kind: Literal["profile.revoke"] = "profile.revoke"
    serial_number: str
    profile_id: int
    profile_version: int | None = None
    assignment_id: int | None = None


class MobileAppPushRequested(BaseModel):
    kind: Literal["mobile_app.push"] = "mobile_app.push"
    serial_number: str
    mobile_app_id: int
    package_name: str
    package_version: str
    app_version: int | None = None
    assignment_id: int | None = None


class MobileAppRevokeRequested(BaseModel):
    kind: Literal["mobile_app.revoke"] = "mobile_app.revoke"
    serial_number: str
    mobile_app_id: int
    package_name: str
    app_version: int | None = None
    assignment_id: int | None = None


class DeviceCommandRequested(BaseModel):
    kind: Literal["device.command"] = "device.command"
    serial_number: str
    command_id: int
    command_type: str
    parameters: dict[str, Any]
