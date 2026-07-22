from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.common.schemas import PaginatedResponse, Scope
from app.dependencies import get_profile_service, get_reconciler
from app.profiles.reconciler import ProfileAssignmentReconciler
from app.profiles.schemas.profile import (
    AssignmentResponse,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
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
    reconciler: ProfileAssignmentReconciler = Depends(get_reconciler),
) -> ProfileResponse:
    profile = await service.create_profile(data)
    if data.scope.targets:
        await reconciler.recalculate_profile(profile.id)
    await revalidate(["profiles"])
    return ProfileResponse.model_validate(profile)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    service: ProfileService = Depends(get_profile_service),
    reconciler: ProfileAssignmentReconciler = Depends(get_reconciler),
) -> ProfileResponse:
    updated = await service.update_profile(profile_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    if data.scope is not None or data.policy is not None:
        if data.policy is not None:
            await reconciler.recalculate_profile(profile_id, force_push=True)
        else:
            await reconciler.recalculate_profile(profile_id)
    await revalidate(["profiles"])
    return ProfileResponse.model_validate(updated)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: int,
    service: ProfileService = Depends(get_profile_service),
) -> None:
    deleted = await service.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    await revalidate(["profiles"])


@router.get("/{profile_id}/scope", response_model=Scope)
async def get_profile_scope(
    profile_id: int,
    service: ProfileService = Depends(get_profile_service),
) -> Scope:
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return profile.scope


@router.put("/{profile_id}/scope", response_model=Scope)
async def set_profile_scope(
    profile_id: int,
    scope: Scope,
    service: ProfileService = Depends(get_profile_service),
    reconciler: ProfileAssignmentReconciler = Depends(get_reconciler),
) -> Scope:
    updated = await service.update_profile(
        profile_id, ProfileUpdate(scope=scope)
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    await reconciler.recalculate_profile(profile_id)
    await revalidate(["profiles"])
    return updated.scope


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
