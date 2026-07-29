from datetime import datetime, timezone

from app.domains.users.schemas import UserResponse


class TestUserSchemas:
    def test_response(self) -> None:
        now = datetime.now(timezone.utc)
        data = UserResponse(
            id=1,
            name="jdoe",
            email="j@example.com",
            permissions=frozenset({"admin"}),
            created_at=now,
            updated_at=now,
        )
        assert data.name == "jdoe"

    def test_response_with_email(self) -> None:
        now = datetime.now(timezone.utc)
        data = UserResponse(
            id=1,
            name="test",
            email="bad@example.com",
            permissions=frozenset({"editor"}),
            created_at=now,
            updated_at=now,
        )
        assert data.email == "bad@example.com"
