from datetime import datetime, timezone
from typing import cast

from app.domains.users.enums import Permission
from app.domains.users.schemas import UserResponse


class TestUserSchemas:
    def test_response(self) -> None:
        now = datetime.now(timezone.utc)
        permissions = cast(frozenset[Permission], frozenset({"admin"}))
        data = UserResponse(
            id=1,
            name="jdoe",
            email="j@example.com",
            permissions=permissions,
            created_at=now,
            updated_at=now,
        )
        assert data.name == "jdoe"

    def test_response_with_email(self) -> None:
        now = datetime.now(timezone.utc)
        permissions = cast(frozenset[Permission], frozenset({"editor"}))
        data = UserResponse(
            id=1,
            name="test",
            email="bad@example.com",
            permissions=permissions,
            created_at=now,
            updated_at=now,
        )
        assert data.email == "bad@example.com"
