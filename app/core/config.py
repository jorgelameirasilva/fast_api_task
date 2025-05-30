import os
from typing import List, Optional
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

    # Azure Storage settings
    AZURE_STORAGE_ACCOUNT: str = os.getenv("AZURE_STORAGE_ACCOUNT", "")
    AZURE_STORAGE_CONTAINER: str = os.getenv("AZURE_STORAGE_CONTAINER", "")
    STORAGE_CONNECTION_STRING: str = os.getenv("STORAGE_CONNECTION_STRING", "")

    # Azure Search settings
    AZURE_SEARCH_SERVICE: str = os.getenv("AZURE_SEARCH_SERVICE", "")
    AZURE_SEARCH_INDEX: str = os.getenv("AZURE_SEARCH_INDEX", "")
    SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")
    AZURE_SEARCH_QUERY_LANGUAGE: str = os.getenv("AZURE_SEARCH_QUERY_LANGUAGE", "en-us")
    AZURE_SEARCH_QUERY_SPELLER: str = os.getenv("AZURE_SEARCH_QUERY_SPELLER", "lexicon")

    # Knowledge Base fields
    KB_FIELDS_CONTENT: str = os.getenv("KB_FIELDS_CONTENT", "content")
    KB_FIELDS_SOURCEPAGE: str = os.getenv("KB_FIELDS_SOURCEPAGE", "sourcepage")

    # OpenAI settings
    OPENAI_HOST: str = os.getenv("OPENAI_HOST", "azure")
    OPENAI_CHATGPT_MODEL: str = os.getenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-4o")
    OPENAI_EMB_MODEL: str = os.getenv(
        "AZURE_OPENAI_EMB_MODEL", "text-embedding-ada-002"
    )

    # Azure OpenAI settings (used when OPENAI_HOST == "azure")
    AZURE_OPENAI_SERVICE: str = os.getenv("AZURE_OPENAI_SERVICE", "")
    AZURE_OPENAI_CHATGPT_DEPLOYMENT: str = os.getenv(
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT", ""
    )
    AZURE_OPENAI_EMB_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT", "")

    # Non-Azure OpenAI settings (used when OPENAI_HOST != "azure")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_ORGANIZATION: str = os.getenv("OPENAI_ORGANIZATION", "")

    # Authentication settings
    AZURE_USE_AUTHENTICATION: bool = (
        os.getenv("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    )
    AZURE_SERVER_APP_ID: str = os.getenv("AZURE_SERVER_APP_ID", "")
    AZURE_SERVER_APP_SECRET: str = os.getenv("AZURE_SERVER_APP_SECRET", "")
    AZURE_CLIENT_APP_ID: str = os.getenv("AZURE_CLIENT_APP_ID", "")
    AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "")
    TOKEN_CACHE_PATH: str = os.getenv("TOKEN_CACHE_PATH", "")

    # Legacy AUTH_ENABLED for backward compatibility
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "false").lower() == "true"

    model_config = SettingsConfigDict(
        case_sensitive=True, env_file=".env", extra="ignore"
    )

    @property
    def azure_search_endpoint(self) -> str:
        """Construct Azure Search endpoint URL"""
        if self.AZURE_SEARCH_SERVICE:
            return f"https://{self.AZURE_SEARCH_SERVICE}.search.windows.net"
        return ""

    @property
    def azure_openai_endpoint(self) -> str:
        """Construct Azure OpenAI endpoint URL"""
        if self.AZURE_OPENAI_SERVICE:
            return f"https://{self.AZURE_OPENAI_SERVICE}.openai.azure.com"
        return ""

    @property
    def azure_storage_account_url(self) -> str:
        """Construct Azure Storage account URL"""
        if self.AZURE_STORAGE_ACCOUNT:
            return f"https://{self.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"
        return ""


settings = Settings()
