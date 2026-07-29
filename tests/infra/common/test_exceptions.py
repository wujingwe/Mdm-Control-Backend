from app.infra.core.exceptions import ConflictError


class TestExceptions:
    def test_conflict_error_default(self) -> None:
        exc = ConflictError()
        assert exc.status_code == 409
        assert exc.detail == "Resource already exists"

    def test_conflict_error_custom(self) -> None:
        exc = ConflictError("Duplicate name")
        assert exc.detail == "Duplicate name"
