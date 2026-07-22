from datetime import datetime, timezone

from app.common.schemas import Scope
from app.profiles.schemas.policy import Policy
from app.profiles.schemas.profile import ProfileResponse


class TestProfileSchemas:
    def test_response(self) -> None:
        data = ProfileResponse(
            id=1,
            name="Profile A",
            version=1,
            policy=Policy(),
            scope=Scope(),
            created_at=datetime.now(timezone.utc),
            created_by=1,
        )
        assert data.name == "Profile A"
        assert data.version == 1

    def test_response_with_policy(self) -> None:
        data = ProfileResponse(
            id=1,
            name="Profile A",
            version=1,
            policy=Policy(screenCaptureDisabled=True),
            scope=Scope(),
            created_at=datetime.now(timezone.utc),
            created_by=1,
        )
        assert data.policy.screenCaptureDisabled is True
