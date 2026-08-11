from typing import cast

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.enums import Permission
from app.domains.users.schemas import UserCreate
from app.domains.users.repositories import UserRepository


class TestUsersAPI:
    async def test_list_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_get_user_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/users/999")
        assert resp.status_code == 404

    async def test_get_by_email_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/users/by-email/nobody@example.com")
        assert resp.status_code == 404

    async def test_create_and_get_user(self, client: AsyncClient, db_session: AsyncSession) -> None:
        create_resp = await client.post(
            "/api/v1/users",
            json={"name": "Alice", "email": "alice@example.com", "permissions": ["admin"]},
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        get_resp = await client.get(f"/api/v1/users/{user_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["email"] == "alice@example.com"

    async def test_update_user_not_found(self, client: AsyncClient) -> None:
        resp = await client.put("/api/v1/users/999", json={"name": "Nope"})
        assert resp.status_code == 404

    async def test_update_user(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        user = await repo.create(UserCreate(email="update@me.com", name="Before", permissions=cast(frozenset[Permission], frozenset({"admin"}))))
        resp = await client.put(f"/api/v1/users/{user.id}", json={"name": "After"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "After"

    async def test_delete_user_not_found(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/v1/users/999")
        assert resp.status_code == 404

    async def test_delete_user(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        user = await repo.create(UserCreate(email="delete@me.com", name="Delete Me", permissions=cast(frozenset[Permission], frozenset({"admin"}))))
        resp = await client.delete(f"/api/v1/users/{user.id}")
        assert resp.status_code == 204

        get_resp = await client.get(f"/api/v1/users/{user.id}")
        assert get_resp.status_code == 404
