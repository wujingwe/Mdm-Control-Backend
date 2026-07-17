
from app.base import Base, utcnow
from app.mobile_apps.schemas import Scope

class Scope(BaseModel):
    targets: list[Target] = []
    exclusions: list[Exclusion] = []


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
