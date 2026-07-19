from pydantic import BaseModel, ConfigDict

from app.common.schemas import Scope


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
