from datetime import datetime

from app.common.schemas import CamelModel, Scope


class MobileAppResponse(CamelModel):
    id: int
    name: str
    enabled: bool
    version: str
    package_name: str
    scope: Scope
    created_by: int
    created_at: datetime
    updated_at: datetime


class MobileAppCreate(CamelModel):
    name: str
    enabled: bool
    version: str
    package_name: str
    scope: Scope


class MobileAppUpdate(CamelModel):
    name: str | None = None
    enabled: bool | None = None
    version: str | None = None
    scope: Scope | None = None
