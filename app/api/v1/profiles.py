from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.common.enums import TargetType
from app.common.schemas import Message, PaginatedResponse
from app.dependencies import get_profile_service
from app.profiles.schemas import (
    AssignmentResponse,
    ProfileCreate,
    ProfileResponse,
    ProfileScopeResponse,
    ProfileUpdate,
    ScopeTarget,
    StatusUpdate,
)
from app.profiles.services import ProfileService
from app.webhook_client import revalidate

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get("", response_model=PaginatedResponse[ProfileResponse])
async def list_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ProfileService = Depends(get_profile_service),
) -> PaginatedResponse[ProfileResponse]:
    items, total = await service.list_profiles(skip=skip, limit=limit)
    return PaginatedResponse(
        items=[ProfileResponse.model_validate(p) for p in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return ProfileResponse.model_validate(profile)


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: ProfileCreate,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    profile = await service.create_profile(data)
    await revalidate(["profiles"])
    return ProfileResponse.model_validate(profile)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    updated = await service.update_profile(profile_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    await revalidate(["profiles"])
    return ProfileResponse.model_validate(updated)


@router.delete("/{profile_id}", response_model=Message)
async def delete_profile(
    profile_id: int,
    service: ProfileService = Depends(get_profile_service),
) -> Message:
    deleted = await service.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    await revalidate(["profiles"])
    return Message(detail="Profile deleted")


@router.get("/{profile_id}/scope", response_model=ProfileScopeResponse)
async def get_profile_scope(
    profile_id: int,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileScopeResponse:
    scope = await service.get_scope(profile_id)
    return ProfileScopeResponse(
        profile_id=profile_id,
        scope=[
            ScopeTarget(target_type=TargetType(s.target_type), target_id=s.target_id)
            for s in scope
        ],
    )


@router.put("/{profile_id}/scope", response_model=ProfileScopeResponse)
async def set_profile_scope(
    profile_id: int,
    scope: list[ScopeTarget],
    service: ProfileService = Depends(get_profile_service),
) -> ProfileScopeResponse:
    await service.set_scope(profile_id, scope)
    await revalidate(["profiles"])
    updated_scope = await service.get_scope(profile_id)
    return ProfileScopeResponse(
        profile_id=profile_id,
        scope=[
            ScopeTarget(target_type=TargetType(s.target_type), target_id=s.target_id)
            for s in updated_scope
        ],
    )


@router.get("/{profile_id}/assignments", response_model=list[AssignmentResponse])
async def list_assignments(
    profile_id: int,
    service: ProfileService = Depends(get_profile_service),
) -> list[AssignmentResponse]:
    assignments = await service.get_assignments(profile_id)
    return [AssignmentResponse.model_validate(a) for a in assignments]


@router.put(
    "/{profile_id}/assignments/{device_id}/status", response_model=AssignmentResponse
)
async def update_assignment_status(
    profile_id: int,
    device_id: int,
    data: StatusUpdate,
    service: ProfileService = Depends(get_profile_service),
) -> AssignmentResponse:
    assignment = await service.update_assignment_status(
        profile_id, device_id, data.status.value
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )
    await revalidate(["profiles"])
    return AssignmentResponse.model_validate(assignment)
