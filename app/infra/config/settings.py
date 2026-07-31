from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = "mysql+aiomysql://jing-weiwu:mdm@localhost:3306/mdm_control"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    webhook_url: str = "http://localhost:3000/api/v1/revalidate"
    revalidation_secret: str = ""

    sso_jwks_url: str = ""
    sso_issuer: str = ""
    sso_audience: str = ""

    dev_auth_enabled: bool = False
    dev_auth_private_key: str = ""

    cors_origins: list[str] = ["*"]

    mock_db: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
