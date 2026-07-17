
from app.base import Base, utcnow
from app.mobile_apps.schemas import Scope

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


###

class ScopeType(TypeDecorator[Scope]):
    impl = JSON

    def process_bind_param(self, value: Scope | None, dialect: Dialect) -> dict[str, Any] | None:
        if value is None:
            return None
        return value.model_dump()

    def process_result_value(self, value: dict[str, Any] | None, dialect: Dialect) -> Scope | None:
        if value is None:
            return None
        return Scope.model.validate(value)


class MobileApp(Base):
    __tablename__ = "mobile_apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[str] = mapped_column(String(32))
    package_name: Mapped[str] = mapped_column(String(64))
    scope: Mapped[Scope] = mapped_column(ScopeType)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datatime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
