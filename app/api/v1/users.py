from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.users.models import User
from app.users.schemas import UserResponse
from app.common.schemas import PaginatedResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserResponse]:
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = [UserResponse.model_validate(u) for u in result.scalars().all()]
    count_stmt = select(User)
    count_result = await db.execute(count_stmt)
    total = len(list(count_result.scalars().all()))
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> UserResponse:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.get("/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)) -> UserResponse:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)
