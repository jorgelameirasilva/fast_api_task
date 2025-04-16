import os
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Ascendion API"

    API_V1_STR: str = ""

    DATABASE_URL: PostgresDsn = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/taskdb"
    )

    CORS_ORIGINS: list[str] = ["*"]

    DEBUG: bool = os.getenv("DEBUG", "0") == "1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env"
    )


settings = Settings()
