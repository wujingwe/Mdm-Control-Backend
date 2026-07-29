from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.infra.core.security import verify_token, _fetch_jwks

_VALID_JWK = '{"keys": [{"kty": "RSA", "n": "gSf7WLI6BPzA5So5h4ZLF8Yc4mHqT0fY3tR0x0C0hVk", "e": "AQAB"}]}'


class TestSecurity:
    async def test_verify_token_no_sso(self) -> None:
        token = jwt.encode({"sub": "user1", "email": "a@b.com", "roles": ["admin"]}, "secret", algorithm="HS256")
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token
        with patch("app.infra.core.security.settings") as mock_settings:
            mock_settings.sso_enabled = False
            result = await verify_token(credentials=creds)
        assert result["sub"] == "user1"
        assert result["email"] == "a@b.com"
        assert result["roles"] == ["admin"]

    async def test_verify_token_sso_path(self) -> None:
        token = jwt.encode({"sub": "sso_user", "email": "sso@b.com"}, "secret", algorithm="HS256")
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token
        with patch("app.infra.core.security.settings") as mock_settings:
            mock_settings.sso_enabled = True
            mock_settings.sso_audience = "test"
            mock_settings.sso_issuer = "test"
            with patch("app.infra.core.security._verify_sso", new_callable=AsyncMock) as mock_verify:
                mock_verify.return_value = {"sub": "sso_user", "email": "sso@b.com"}
                result = await verify_token(credentials=creds)
        assert result["sub"] == "sso_user"
        mock_verify.assert_awaited_once_with(token)

    async def test_verify_token_invalid(self) -> None:
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = "not-a-valid-token"
        with patch("app.infra.core.security.settings") as mock_settings:
            mock_settings.sso_enabled = False
            with pytest.raises(HTTPException) as exc:
                await verify_token(credentials=creds)
        assert exc.value.status_code == 401

    async def test_verify_token_missing_sub_and_email(self) -> None:
        token = jwt.encode({"roles": []}, "secret", algorithm="HS256")
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token
        with patch("app.infra.core.security.settings") as mock_settings:
            mock_settings.sso_enabled = False
            result = await verify_token(credentials=creds)
        assert result["sub"] == ""
        assert result["email"] == ""
        assert result["name"] == ""

    async def test_fetch_jwks_no_url(self) -> None:
        with patch("app.infra.core.security.settings") as mock_settings:
            mock_settings.sso_jwks_url = ""
            with pytest.raises(HTTPException) as exc:
                await _fetch_jwks()
        assert exc.value.status_code == 500

    async def test_fetch_jwks_from_cache(self) -> None:
        from app.infra.core.security import _jwks_cache

        _jwks_cache.clear()
        mock_jwks = object()
        _jwks_cache["jwks"] = mock_jwks
        _jwks_cache["fetched_at"] = 9999999999.0
        result = await _fetch_jwks()
        assert result is mock_jwks

    async def test_fetch_jwks_fetches_from_server(self) -> None:
        from app.infra.core.security import _jwks_cache

        _jwks_cache.clear()
        mock_response = MagicMock()
        mock_response.text = _VALID_JWK

        with patch("app.infra.core.security.settings") as mock_settings:
            mock_settings.sso_jwks_url = "https://example.com/.well-known/jwks.json"
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                result = await _fetch_jwks()
        assert result is not None
