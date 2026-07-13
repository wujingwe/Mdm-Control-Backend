from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_extension_attribute_service
from app.common.schemas import Message, PaginatedResponse
from app.extension_attributes.schemas import (
    ExtensionAttributeCreate,
    ExtensionAttributeResponse,
    ExtensionAttributeUpdate,
)
from app.extension_attributes.services import ExtensionAttributeService
from app.webhook_client import revalidate

router = APIRouter(prefix="/extension-attributes", tags=["Extension Attributes"])


@router.get("", response_model=PaginatedResponse[ExtensionAttributeResponse])
async def list_extension_attributes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ExtensionAttributeService = Depends(get_extension_attribute_service),
) -> PaginatedResponse[ExtensionAttributeResponse]:
    items, total = await service.list_attributes(skip=skip, limit=limit)
    return PaginatedResponse(
        items=[ExtensionAttributeResponse.model_validate(a) for a in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/{attribute_id}", response_model=ExtensionAttributeResponse)
async def get_extension_attribute(
    attribute_id: int,
    service: ExtensionAttributeService = Depends(get_extension_attribute_service),
) -> ExtensionAttributeResponse:
    attr = await service.get_attribute(attribute_id)
    if not attr:
        raise HTTPException(status_code=404, detail="Extension attribute not found")
    return ExtensionAttributeResponse.model_validate(attr)


@router.post("", response_model=ExtensionAttributeResponse, status_code=201)
async def create_extension_attribute(
    data: ExtensionAttributeCreate,
    service: ExtensionAttributeService = Depends(get_extension_attribute_service),
) -> ExtensionAttributeResponse:
    attr = await service.create_attribute(data)
    await revalidate(["extension-attributes"])
    return ExtensionAttributeResponse.model_validate(attr)


@router.put("/{attribute_id}", response_model=ExtensionAttributeResponse)
async def update_extension_attribute(
    attribute_id: int,
    data: ExtensionAttributeUpdate,
    service: ExtensionAttributeService = Depends(get_extension_attribute_service),
) -> ExtensionAttributeResponse:
    existing = await service.get_attribute(attribute_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Extension attribute not found")
    updated = await service.update_attribute(attribute_id, data)
    await revalidate(["extension-attributes"])
    return ExtensionAttributeResponse.model_validate(updated)


@router.delete("/{attribute_id}", response_model=Message)
async def delete_extension_attribute(
    attribute_id: int,
    service: ExtensionAttributeService = Depends(get_extension_attribute_service),
) -> Message:
    deleted = await service.delete_attribute(attribute_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Extension attribute not found")
    await revalidate(["extension-attributes"])
    return Message(detail="Extension attribute deleted")
