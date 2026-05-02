import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WILMA_", env_file=".env", extra="ignore")

    base_url: str = "https://raseborg.inschool.fi"
    username: str
    password: str
    # Session timeout in seconds
    session_timeout: int = 30


settings = Settings(_env_file=os.environ.get("WILMA_ENV_FILE", ".env"))  # type: ignore[call-arg]
