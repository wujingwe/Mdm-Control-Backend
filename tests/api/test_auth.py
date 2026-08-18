from typing import cast
from unittest.mock import patch

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.enums import Permission
from app.domains.users.schemas import UserCreate
from app.domains.users.repositories import UserRepository
from app.infra.core.dev_auth import get_jwks


@pytest.mark.skip(reason="DEV_AUTH_PRIVATE_KEY")
@pytest.mark.asyncio
async def test_jwks_endpoint_returns_public_keys(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/jwks")
    assert response.status_code == 200
    assert response.json()["keys"][0]["kty"] == "RSA"
    assert response.json()["keys"][0]["alg"] == "RS256"


@pytest.mark.asyncio
async def test_current_user_returns_authenticated_user(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_dev_token_disabled_returns_403(client: AsyncClient) -> None:
    with patch("app.api.v1.auth.settings") as mock_settings:
        mock_settings.dev_auth_enabled = False
        response = await client.post("/api/v1/auth/dev-token", json={"email": "test@example.com"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_dev_token_unknown_user_returns_404(client: AsyncClient) -> None:
    with patch("app.api.v1.auth.settings") as mock_settings:
        mock_settings.dev_auth_enabled = True
        response = await client.post("/api/v1/auth/dev-token", json={"email": "missing@example.com"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dev_token_rejects_client_supplied_roles(client: AsyncClient) -> None:
    with patch("app.api.v1.auth.settings") as mock_settings:
        mock_settings.dev_auth_enabled = True
        response = await client.post(
            "/api/v1/auth/dev-token",
            json={"email": "test@example.com", "roles": ["admin"]},
        )
    assert response.status_code == 422


@pytest.mark.skip(reason="DEV_AUTH_PRIVATE_KEY")
@pytest.mark.asyncio
async def test_dev_token_mints_verifiable_jwt(client: AsyncClient, db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    existing = await repo.get_by_email("test@example.com")
    if existing is None:
        await repo.create(
            UserCreate(
                email="test@example.com",
                name="Test User",
                permissions=cast(frozenset[Permission], frozenset({"admin"})),
            )
        )
    with patch("app.api.v1.auth.settings") as mock_settings:
        mock_settings.dev_auth_enabled = True
        mock_settings.sso_issuer = "http://test"
        mock_settings.sso_audience = "tmdm-api"
        response = await client.post("/api/v1/auth/dev-token", json={"email": "test@example.com"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "Bearer"
    kid = jwt.get_unverified_header(token)["kid"]
    signing_key = jwt.PyJWKSet.from_json(get_jwks().model_dump_json())[kid]
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience="tmdm-api",
        issuer="http://test",
    )
    assert payload["email"] == "test@example.com"
    assert "admin" in payload["roles"]
