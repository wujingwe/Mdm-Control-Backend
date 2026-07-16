class TestUsersAPI:
    async def test_list_empty(self, client):
        resp = await client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_get_user_not_found(self, client):
        resp = await client.get("/api/v1/users/999")
        assert resp.status_code == 404

    async def test_get_by_email_not_found(self, client):
        resp = await client.get("/api/v1/users/by-email/nobody@example.com")
        assert resp.status_code == 404
