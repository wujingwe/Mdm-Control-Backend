from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domains.users.models import User
from app.infra.config.settings import settings
from app.dependencies import get_current_user
from app.domains.users.schemas import UserResponse
from app.infra.core.dev_auth import DEV_TOKEN_TTL_SECONDS, JwksResponse, get_jwks, mint_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class DevTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    name: str = ""


class DevTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = DEV_TOKEN_TTL_SECONDS


@router.get("/jwks")
async def dev_jwks() -> JwksResponse:
    return get_jwks()


@router.get("/me", response_model=UserResponse)
async def current_user(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/dev-token", response_model=DevTokenResponse)
async def create_dev_token(
    data: DevTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> DevTokenResponse:
    if not settings.dev_auth_enabled:
        raise HTTPException(status_code=403, detail="Dev auth is disabled")

    user = await db.scalar(select(User).where(User.email == data.email))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    token = mint_token(
        email=user.email,
        sub=str(user.id),
        roles=[str(p) for p in user.permissions],
        issuer=settings.sso_issuer or "http://localhost:8000",
        audience=settings.sso_audience or "tmdm-api",
        name=data.name or user.name,
    )
    return DevTokenResponse(access_token=token)
