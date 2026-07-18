from datetime import datetime, timezone

from app.profiles.schemas import ProfileResponse


class TestProfileSchemas:
    def test_response(self) -> None:
        data = ProfileResponse(
            id=1,
            name="Profile A",
            version=1,
            created_at=datetime.now(timezone.utc),
            created_by=1,
        )
        assert data.name == "Profile A"
        assert data.version == 1
