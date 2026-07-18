from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.smart_groups.schemas import SmartGroupCreate, SmartGroupResponse, SmartGroupUpdate


class TestSmartGroupSchemas:
    def test_create_valid(self):
        data = SmartGroupCreate(
            name="Group A",
            criteria=[{"field": "os_version", "operator": "is", "type": "string", "value": "Android 14"}],
        )
        assert data.name == "Group A"
        assert len(data.criteria) == 1

    def test_create_with_description(self):
        data = SmartGroupCreate(
            name="Group A",
            description="desc",
            criteria=[{"field": "os_version", "operator": "is", "type": "string", "value": "Android 14"}],
        )
        assert data.description == "desc"

    def test_create_empty_criteria_rejected(self):
        with pytest.raises(ValidationError):
            SmartGroupCreate(name="Group A", criteria=[])

    def test_update_partial(self):
        data = SmartGroupUpdate(description="Updated desc")
        assert data.model_dump(exclude_unset=True) == {"description": "Updated desc"}

    def test_response(self):
        now = datetime.now(timezone.utc)
        data = SmartGroupResponse(id=1, name="Group A", created_by=1, created_at=now)
        assert data.id == 1
