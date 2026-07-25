from datetime import datetime


from app.common.enums import ExtensionDataType, ExtensionInputType
from app.common.schemas import CamelModel


class ExtensionAttributeCreate(CamelModel):
    name: str
    description: str | None = None
    data_type: ExtensionDataType
    input_type: ExtensionInputType
    popup_choices: list[str] | None = None


class ExtensionAttributeUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    data_type: ExtensionDataType | None = None
    input_type: ExtensionInputType | None = None
    popup_choices: list[str] | None = None


class ExtensionAttributeResponse(CamelModel):
    id: int
    name: str
    description: str | None = None
    data_type: ExtensionDataType
    input_type: ExtensionInputType
    popup_choices: list[str] | None = None
    created_at: datetime
    created_by: int
    updated_at: datetime | None = None
