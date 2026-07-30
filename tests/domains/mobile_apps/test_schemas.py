from datetime import datetime, timezone

from app.domains.shared.scope import Scope
from app.domains.mobile_apps.schemas import MobileAppResponse


class TestMobileAppSchemas:
    def test_response(self) -> None:
        now = datetime.now(timezone.utc)
        data = MobileAppResponse(
            id=1,
            name="Outlook",
            enabled=True,
            package_version="4.75.0",
            package_name="com.microsoft.office.outlook",
            version=1,
            scope=Scope(),
            created_by=1,
            created_at=now,
            updated_at=now,
        )
        assert data.name == "Outlook"
        assert data.package_version == "4.75.0"
        assert data.version == 1

    def test_response_with_scope(self) -> None:
        now = datetime.now(timezone.utc)
        data = MobileAppResponse(
            id=2,
            name="Teams",
            enabled=True,
            package_version="24.12.0",
            package_name="com.microsoft.teams",
            version=2,
            scope=Scope(targets=[]),
            created_by=1,
            created_at=now,
            updated_at=now,
        )
        assert data.scope.targets == []
