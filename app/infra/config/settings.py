# The pydantic mypy plugin reports an internal generated ``Any`` on this model.
# The fields below are explicitly typed; keep the exception scoped to this module.
# mypy: disable-error-code=explicit-any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_url: str = ""
    integration_db_url: str = ""
    rabbitmq_url: str = ""
    webhook_url: str = "http://localhost:3000/api/v1/revalidate"
    revalidation_secret: str = ""

    sse_secret: str = ""

    sweep_secret: str = ""

    sso_jwks_url: str = ""
    sso_issuer: str = ""
    sso_audience: str = ""

    dev_auth_enabled: bool = False
    dev_auth_private_key: str = ""

    cors_origins: list[str] = ["*"]

    mock_db: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
