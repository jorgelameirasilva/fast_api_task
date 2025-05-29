import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Chat Application"

    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "0") == "1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]

    # Static files settings
    STATIC_DIR: str = "static"
    CONTENT_DIR: str = "content"

    # Azure/OpenAI settings (placeholders for now)
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

    # Search settings
    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AZURE_SEARCH_API_KEY: str = os.getenv("AZURE_SEARCH_API_KEY", "")
    AZURE_SEARCH_INDEX: str = os.getenv("AZURE_SEARCH_INDEX", "")

    # Storage settings
    AZURE_STORAGE_ACCOUNT: str = os.getenv("AZURE_STORAGE_ACCOUNT", "")
    AZURE_STORAGE_CONTAINER: str = os.getenv("AZURE_STORAGE_CONTAINER", "")
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING", ""
    )

    # Authentication settings
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "false").lower() == "true"

    model_config = SettingsConfigDict(
        case_sensitive=True, env_file=".env", extra="ignore"
    )


settings = Settings()
