from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.infra.core.dev_auth import get_jwks, mint_token

_RSA_PEM = (
    rsa.generate_private_key(public_exponent=65537, key_size=2048)
    .private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    .decode("utf-8")
)


def test_get_jwks_returns_rsa_public_key() -> None:
    with patch("app.infra.core.dev_auth._private_key", None):
        with patch("app.infra.core.dev_auth.settings") as mock_settings:
            mock_settings.dev_auth_private_key = _RSA_PEM
            jwks = get_jwks()
    assert jwks.keys[0].kty == "RSA"
    assert jwks.keys[0].alg == "RS256"
    assert jwks.keys[0].use == "sig"
    assert jwks.keys[0].kid == "dev-key"
    assert jwks.keys[0].n
    assert jwks.keys[0].e


def test_mint_token_roundtrip() -> None:
    with patch("app.infra.core.dev_auth._private_key", None):
        with patch("app.infra.core.dev_auth.settings") as mock_settings:
            mock_settings.dev_auth_private_key = _RSA_PEM
            token = mint_token(
                email="admin@example.com",
                sub="1",
                roles=["admin"],
                issuer="http://localhost:8000",
                audience="tmdm-api",
            )
            jwks = get_jwks()
    kid = jwt.get_unverified_header(token)["kid"]
    signing_key = jwt.PyJWKSet.from_json(jwks.model_dump_json())[kid]
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience="tmdm-api",
        issuer="http://localhost:8000",
    )
    assert payload["email"] == "admin@example.com"
    assert payload["preferred_username"] == "admin@example.com"
    assert payload["roles"] == ["admin"]
    assert payload["sub"] == "1"


def test_mint_token_serializes_jwks() -> None:
    with patch("app.infra.core.dev_auth._private_key", None):
        with patch("app.infra.core.dev_auth.settings") as mock_settings:
            mock_settings.dev_auth_private_key = _RSA_PEM
            jwks_json = get_jwks().model_dump_json()
    assert "keys" in jwks_json


def test_missing_private_key_fails_clearly() -> None:
    with patch("app.infra.core.dev_auth._private_key", None):
        with patch("app.infra.core.dev_auth.settings") as mock_settings:
            mock_settings.dev_auth_private_key = ""
            with pytest.raises(RuntimeError, match="DEV_AUTH_PRIVATE_KEY"):
                get_jwks()
