from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = "mysql+aiomysql://jing-weiwu:mdm@localhost:3306/mdm_control"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "policy-assignments"
    kafka_group_id: str = "mdm-control-group"
    webhook_url: str = "http://localhost:3000/api/v1/revalidate"
    revalidation_secret: str = ""
    sse_server_url: str = "http://0.0.0.0:8080/notify"

    sso_enabled: bool = False
    sso_jwks_url: str = ""
    sso_issuer: str = ""
    sso_audience: str = ""

    cors_origins: list[str] = ["*"]

    mock_db: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
