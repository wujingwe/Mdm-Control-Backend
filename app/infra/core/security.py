import asyncio
import logging
import time
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infra.config.settings import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, Any] = {}
_jwks_fetch_lock = asyncio.Lock()
JWKS_CACHE_TTL = 3600


async def _fetch_jwks() -> jwt.PyJWKSet:
    async with _jwks_fetch_lock:
        now = time.time()
        cached = _jwks_cache.get("fetched_at")
        if cached and now - cached < JWKS_CACHE_TTL:
            return _jwks_cache["jwks"]  # type: ignore[no-any-return]

        if not settings.sso_jwks_url:
            logger.warning("Auth: SSO_JWKS_URL is not configured")
            raise HTTPException(
                status_code=500,
                detail="SSO_JWKS_URL is not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(settings.sso_jwks_url)
                resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Auth: failed to fetch JWKS from %s: %s", settings.sso_jwks_url, e)
            raise

        jwks: jwt.PyJWKSet = jwt.PyJWKSet.from_json(resp.text)
        _jwks_cache["jwks"] = jwks
        _jwks_cache["fetched_at"] = time.time()
        return jwks


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> dict[str, Any]:
    if credentials is None:
        logger.warning("Auth: no Authorization header (missing Bearer token)")
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    logger.info("Auth: verifying token (token_length=%s)", len(token))
    try:
        payload = await _verify_sso(token)

        logger.info("Auth: token verified for sub=%r email=%r", payload.get("sub"), payload.get("email"))
        return {
            "sub": payload.get("sub", ""),
            "email": payload.get("email") or payload.get("preferred_username") or payload.get("upn", ""),
            "name": payload.get("name", ""),
            "roles": payload.get("roles", []),
        }
    except jwt.PyJWTError as e:
        logger.warning("Auth: token validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token") from e


async def _verify_sso(token: str) -> dict[str, Any]:
    jwks = await _fetch_jwks()
    kid = jwt.get_unverified_header(token).get("kid")
    if kid is None:
        raise jwt.exceptions.InvalidKeyError("JWT header is missing kid")
    try:
        signing_key = jwks[kid]
    except KeyError as e:
        raise jwt.exceptions.InvalidKeyError(f"JWKS has no key for kid {kid!r}") from e
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.sso_audience,
        issuer=settings.sso_issuer,
    )
