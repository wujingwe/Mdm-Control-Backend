from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = "mysql+aiomysql://jing-weiwu:mdm@localhost:3306/mdm_control"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "mdm.device.commands"
    rabbitmq_exchange_type: str = "topic"
    rabbitmq_device_routing_key_prefix: str = "device"
    rabbitmq_consumer_queue: str = "sse.commands.local"
    rabbitmq_consumer_binding_keys: list[str] = []
    rabbitmq_prefetch_count: int = 10
    rabbitmq_requeue_on_error: bool = False
    rabbitmq_consumer_enabled: bool = False
    webhook_url: str = "http://localhost:3000/api/v1/revalidate"
    revalidation_secret: str = ""
    sse_server_url: str = "http://0.0.0.0:8080/notify"

    sso_enabled: bool = False
    sso_jwks_url: str = ""
    sso_issuer: str = ""
    sso_audience: str = ""

    cors_origins: list[str] = ["*"]

    mock_db: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
