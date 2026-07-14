from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_user_service
from app.common.schemas import PaginatedResponse
from app.users.schemas import UserResponse
from app.users.services import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserResponse]:
    items = await service.list_users(skip=skip, limit=limit)
    total = await service.count_users()
    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.get("/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(
    email: str,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)
