import asyncio
import logging
import time
from dataclasses import dataclass

import httpx
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.infra.config.settings import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class TokenClaims(BaseModel):
    sub: str
    email: str
    name: str
    roles: list[str]


@dataclass
class _JwksCache:
    jwks: jwt.PyJWKSet
    fetched_at: float


_jwks_cache: _JwksCache | None = None
_jwks_fetch_lock = asyncio.Lock()
JWKS_CACHE_TTL = 3600


async def _fetch_jwks() -> jwt.PyJWKSet:
    global _jwks_cache
    async with _jwks_fetch_lock:
        now = time.time()
        cached = _jwks_cache
        if cached and now - cached.fetched_at < JWKS_CACHE_TTL:
            return cached.jwks

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
        _jwks_cache = _JwksCache(jwks=jwks, fetched_at=time.time())
        return jwks


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> TokenClaims:
    if credentials is None:
        logger.warning("Auth: no Authorization header (missing Bearer token)")
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    logger.info("Auth: verifying token (token_length=%s)", len(token))
    try:
        claims = await _verify_sso(token)

        logger.info("Auth: token verified for sub=%r email=%r", claims.sub, claims.email)
        return claims
    except jwt.PyJWTError as e:
        logger.warning("Auth: token validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token") from e


async def _verify_sso(token: str) -> TokenClaims:
    jwks = await _fetch_jwks()
    kid = jwt.get_unverified_header(token).get("kid")
    if kid is None:
        raise jwt.exceptions.InvalidKeyError("JWT header is missing kid")
    try:
        signing_key = jwks[kid]
    except KeyError as e:
        raise jwt.exceptions.InvalidKeyError(f"JWKS has no key for kid {kid!r}") from e
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.sso_audience,
        issuer=settings.sso_issuer,
    )
    return TokenClaims(
        sub=str(payload.get("sub") or ""),
        email=str(payload.get("email") or payload.get("preferred_username") or payload.get("upn") or ""),
        name=str(payload.get("name") or ""),
        roles=list(payload.get("roles") or []),
    )
