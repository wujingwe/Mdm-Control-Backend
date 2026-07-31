from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.infra.core.security import verify_token, _fetch_jwks

_VALID_JWK = '{"keys": [{"kty": "RSA", "n": "gSf7WLI6BPzA5So5h4ZLF8Yc4mHqT0fY3tR0x0C0hVk", "e": "AQAB"}]}'


class TestSecurity:
    async def test_verify_token_always_uses_sso_path(self) -> None:
        token = jwt.encode({"sub": "user1", "email": "a@b.com", "roles": ["admin"]}, "secret", algorithm="HS256")
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token
        with patch("app.infra.core.security._verify_sso", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"sub": "user1", "email": "a@b.com", "roles": ["admin"]}
            result = await verify_token(credentials=creds)
        assert result["sub"] == "user1"
        assert result["email"] == "a@b.com"
        assert result["roles"] == ["admin"]

    async def test_verify_token_invalid(self) -> None:
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = "not-a-valid-token"
        with patch("app.infra.core.security._verify_sso", new_callable=AsyncMock) as mock_verify:
            mock_verify.side_effect = jwt.InvalidTokenError("invalid")
            with pytest.raises(HTTPException) as exc:
                await verify_token(credentials=creds)
        assert exc.value.status_code == 401

    async def test_verify_token_missing_sub_and_email(self) -> None:
        token = jwt.encode({"roles": []}, "secret", algorithm="HS256")
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token
        with patch("app.infra.core.security._verify_sso", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"roles": []}
            result = await verify_token(credentials=creds)
        assert result["sub"] == ""
        assert result["email"] == ""
        assert result["name"] == ""

    async def test_verify_token_falls_back_to_preferred_username(self) -> None:
        token = jwt.encode({"sub": "u1", "preferred_username": "aad@b.com"}, "secret", algorithm="HS256")
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token
        with patch("app.infra.core.security._verify_sso", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"sub": "u1", "preferred_username": "aad@b.com"}
            result = await verify_token(credentials=creds)
        assert result["email"] == "aad@b.com"

    async def test_verify_token_falls_back_to_upn(self) -> None:
        token = jwt.encode({"sub": "u1", "upn": "domain\\user"}, "secret", algorithm="HS256")
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token
        with patch("app.infra.core.security._verify_sso", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"sub": "u1", "upn": "domain\\user"}
            result = await verify_token(credentials=creds)
        assert result["email"] == "domain\\user"

    async def test_verify_sso_decodes_with_array_audience(self) -> None:
        from unittest.mock import AsyncMock

        import base64

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from app.infra.core import security as security_module

        def _b64url(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_numbers = private_key.public_key().public_numbers()
        n = _b64url(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big"))
        e = _b64url(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big"))
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        jwk_set = jwt.PyJWKSet.from_dict({"keys": [{"kty": "RSA", "n": n, "e": e, "alg": "RS256", "kid": "test-key"}]})
        token = jwt.encode(
            {"sub": "sso_user", "email": "sso@b.com", "aud": ["tmdm-api", "other-client"], "iss": "issuer"},
            pem,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )
        with patch("app.infra.core.security._fetch_jwks", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = jwk_set
            with patch("app.infra.core.security.settings") as mock_settings:
                mock_settings.sso_audience = "tmdm-api"
                mock_settings.sso_issuer = "issuer"
                result = await security_module._verify_sso(token)
        assert result["email"] == "sso@b.com"

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
