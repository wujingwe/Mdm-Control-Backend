from datetime import datetime, timezone

from app.users.schemas import UserResponse


class TestUserSchemas:
    def test_response(self):
        now = datetime.now(timezone.utc)
        data = UserResponse(
            id=1,
            name="jdoe",
            email="j@example.com",
            permissions=["admin"],
            created_at=now,
        )
        assert data.name == "jdoe"

    def test_response_with_email(self):
        now = datetime.now(timezone.utc)
        data = UserResponse(
            id=1,
            name="test",
            email="bad@example.com",
            permissions=["editor"],
            created_at=now,
        )
        assert data.email == "bad@example.com"
