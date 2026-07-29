from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.infra.common.enums import CriteriaType
from app.infra.criteria import Criteria
from app.domains.smart_groups.schemas import (
    SmartGroupCreate,
    SmartGroupResponse,
    SmartGroupUpdate,
)


class TestSmartGroupSchemas:
    def test_create_valid(self) -> None:
        data = SmartGroupCreate(
            name="Group A",
            criteria=[
                Criteria(
                    field="os_version",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="Android 14",
                ),
            ],
        )
        assert data.name == "Group A"
        assert len(data.criteria) == 1

    def test_create_with_description(self) -> None:
        data = SmartGroupCreate(
            name="Group A",
            description="desc",
            criteria=[
                Criteria(
                    field="os_version",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="Android 14",
                ),
            ],
        )
        assert data.description == "desc"

    def test_create_empty_criteria_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SmartGroupCreate(name="Group A", criteria=[])

    def test_update_partial(self) -> None:
        data = SmartGroupUpdate(description="Updated desc")
        assert data.model_dump(exclude_unset=True) == {"description": "Updated desc"}

    def test_response(self) -> None:
        now = datetime.now(timezone.utc)
        data = SmartGroupResponse(
            id=1,
            name="Group A",
            criteria=[
                Criteria(
                    field="os_version",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="Android 14",
                ),
            ],
            created_by=1,
            created_at=now,
            updated_at=now,
        )
        assert data.id == 1
