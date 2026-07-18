from app.common.schemas import Message


class TestCommonSchemas:
    def test_message(self):
        msg = Message(detail="OK")
        assert msg.detail == "OK"
