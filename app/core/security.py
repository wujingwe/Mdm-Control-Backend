import asyncio
import logging
import time

import httpx
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=True)

_jwks_cache: dict = {}
_jwks_fetch_lock = asyncio.Lock()
JWKS_CACHE_TTL = 3600


async def _fetch_jwks() -> jwt.PyJWKSet:
    async with _jwks_fetch_lock:
        now = time.time()
        cached = _jwks_cache.get("fetched_at")
        if cached and now - cached < JWKS_CACHE_TTL:
            return _jwks_cache["jwks"]  # type: ignore[no-any-return]

        if not settings.sso_jwks_url:
            raise HTTPException(
                status_code=500,
                detail="SSO_JWKS_URL is not configured",
            )

        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.sso_jwks_url)
            resp.raise_for_status()

        jwks: jwt.PyJWKSet = jwt.PyJWKSet.from_json(resp.text)  # type: ignore[no-any-return,assignment]
        _jwks_cache["jwks"] = jwks
        _jwks_cache["fetched_at"] = time.time()
        return jwks


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    token = credentials.credentials
    try:
        if settings.sso_enabled:
            payload = await _verify_sso(token)
        else:
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
            )

        return {
            "sub": payload.get("sub", ""),
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
            "roles": payload.get("roles", []),
        }
    except jwt.PyJWTError as e:
        logger.warning("Token validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token") from e


async def _verify_sso(token: str) -> dict:
    jwks = await _fetch_jwks()
    signing_key = jwks.get_signing_key_from_jwt(token)  # type: ignore[attr-defined]
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.sso_audience,
        issuer=settings.sso_issuer,
    )
