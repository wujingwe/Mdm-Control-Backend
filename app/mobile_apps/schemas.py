from pydantic import BaseModel, ConfigDict


class Target(BaseModel):
    smart_groups: list[int] | None = None
    static_groups: list[int] | None = None
    device_serial_numbers: list[str] | None = None


class Exclusion(BaseModel):
    smart_groups: list[int] | None = None
    static_groups: list[int] | None = None
    device_serial_numbers: list[str] | None = None


class Scope(BaseModel):
    targets: list[Target] = []
    exclusions: list[Exclusion] = []


class MobileAppResponse(BaseModel):
    id: int
    name: str
    enabled: bool
    version: str
    package_name: str
    scope: Scope

    model_config = ConfigDict(from_attributes=True)


class MobileAppCreate(BaseModel):
    name: str
    enabled: bool
    version: str
    package_name: str
    scope: Scope


class MobileAppUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    version: str | None = None
    scope: Scope | None = None
