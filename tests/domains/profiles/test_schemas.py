from datetime import datetime, timezone

from app.domains.shared.scope import Scope
from app.domains.profiles.schemas.policy import Policy
from app.domains.profiles.schemas.profile import ProfileResponse


class TestProfileSchemas:
    def test_response(self) -> None:
        now = datetime.now(timezone.utc)
        data = ProfileResponse(
            id=1,
            name="Profile A",
            version=1,
            policy=Policy(),
            scope=Scope(),
            created_at=now,
            updated_at=now,
            created_by=1,
        )
        assert data.name == "Profile A"
        assert data.version == 1

    def test_response_with_policy(self) -> None:
        now = datetime.now(timezone.utc)
        data = ProfileResponse(
            id=1,
            name="Profile A",
            version=1,
            policy=Policy(screenCaptureDisabled=True),
            scope=Scope(),
            created_at=now,
            updated_at=now,
            created_by=1,
        )
        assert data.policy.screenCaptureDisabled is True
