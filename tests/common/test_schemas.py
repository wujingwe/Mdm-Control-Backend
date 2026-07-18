from app.common.schemas import Message


class TestCommonSchemas:
    def test_message(self) -> None:
        msg = Message(detail="OK")
        assert msg.detail == "OK"
