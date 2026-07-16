from app.core.exceptions import ConflictError


class TestExceptions:
    def test_conflict_error_default(self):
        exc = ConflictError()
        assert exc.status_code == 409
        assert exc.detail == "Resource already exists"

    def test_conflict_error_custom(self):
        exc = ConflictError("Duplicate name")
        assert exc.detail == "Duplicate name"
