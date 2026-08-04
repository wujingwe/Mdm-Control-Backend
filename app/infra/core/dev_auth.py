import base64
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.infra.config.settings import settings

DEV_TOKEN_TTL_SECONDS = 3600


def _encode_base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _parse_private_key(pem: bytes) -> rsa.RSAPrivateKey:
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("dev_auth_private_key must be an RSA private key")
    return key


def _load_private_key() -> rsa.RSAPrivateKey:
    if not settings.dev_auth_private_key:
        raise RuntimeError("DEV_AUTH_PRIVATE_KEY must be configured for local dev auth")
    return _parse_private_key(settings.dev_auth_private_key.encode("utf-8"))


_private_key: rsa.RSAPrivateKey | None = None


def _get_private_key() -> rsa.RSAPrivateKey:
    global _private_key
    if _private_key is None:
        _private_key = _load_private_key()
    return _private_key


def get_jwks() -> dict[str, Any]:
    public_key = _get_private_key().public_key()
    numbers = public_key.public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "n": _encode_base64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
                "e": _encode_base64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
                "use": "sig",
                "alg": "RS256",
                "kid": "dev-key",
            }
        ]
    }


def mint_token(
    email: str,
    sub: str,
    roles: list[str],
    *,
    issuer: str,
    audience: str,
    expires_in: int = DEV_TOKEN_TTL_SECONDS,
    name: str = "",
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": sub,
        "email": email,
        "preferred_username": email,
        "name": name,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, _get_private_key(), algorithm="RS256", headers={"kid": "dev-key"})
