from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.infra.common.schemas import PaginatedResponse
from app.dependencies import get_user_service, require_permission
from app.domains.users.schemas import UserCreate, UserResponse, UserUpdate
from app.domains.users.services import UserService
from app.webhook_client import revalidate
from app.domains.users.models import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserResponse]:
    items, total = await service.list_users(skip=skip, limit=limit)
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


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
    _current_user: User = Depends(require_permission("editor")),
) -> UserResponse:
    user = await service.create_user(data)
    await revalidate(["users"])
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
    _current_user: User = Depends(require_permission("editor")),
) -> UserResponse:
    if not data.model_fields_set:
        user = await service.get_user(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserResponse.model_validate(user)
    updated = await service.update_user(user_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await revalidate(["users"])
    user = await service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    _current_user: User = Depends(require_permission("admin")),
) -> None:
    deleted = await service.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await revalidate(["users"])
