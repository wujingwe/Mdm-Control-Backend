from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.enums import ExtensionDataType, ExtensionInputType


class ExtensionAttributeCreate(BaseModel):
    name: str
    description: str | None = None
    data_type: ExtensionDataType
    input_type: ExtensionInputType
    popup_choices: list[str] | None = None
    created_by: int = 1


class ExtensionAttributeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    data_type: ExtensionDataType | None = None
    input_type: ExtensionInputType | None = None
    popup_choices: list[str] | None = None


class ExtensionAttributeResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    data_type: ExtensionDataType
    input_type: ExtensionInputType
    popup_choices: list[str] | None = None
    created_at: datetime
    created_by: int
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
