import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App Configuration
    app_name: str = "HR Chatbot API"
    debug: bool = False

    # Azure Storage
    AZURE_STORAGE_CLIENT_ID: Optional[str] = None
    AZURE_STORAGE_CLIENT_SECRET: Optional[str] = None
    AZURE_STORAGE_ACCOUNT: str = "stdiagnosticsstorageprod"
    AZURE_STORAGE_CONTAINER: str = "s-alt-0303-asia-or-us3-dlc13-webintelligentchatbot"
    DIAGNOSTICS_STORAGE_CONTAINER: Optional[str] = None

    # Azure Search
    AZURE_SEARCH_SERVICE: Optional[str] = None
    AZURE_SEARCH_INDEX: Optional[str] = None
    AZURE_SEARCH_CLIENT_ID: Optional[str] = None
    AZURE_SEARCH_CLIENT_SECRET: Optional[str] = None
    AZURE_SEARCH_TENANT_ID: Optional[str] = None

    # OpenAI Configuration
    OPENAI_HOST: str = "azure"
    AZURE_OPENAI_CHATGPT_MODEL: str = "gpt-4o"
    AZURE_OPENAI_EMB_MODEL_NAME: str = "text-embedding-ada-002"
    AZURE_OPENAI_SERVICE: str = "saic-azu-eus2-npd-openaioc-specialservices"
    AZURE_OPENAI_CHATGPT_DEPLOYMENT: str = "gpt-4o-chatbot-poc"
    AZURE_OPENAI_EMB_DEPLOYMENT: str = "embeddings"

    # Secure GPT Configuration
    SECURE_GPT_DEPLOYMENT_ID: Optional[str] = None
    SECURE_GPT_EMB_DEPLOYMENT_ID: Optional[str] = None
    SECURE_GPT_CLIENT_ID: Optional[str] = None
    SECURE_GPT_CLIENT_SECRET: Optional[str] = None
    SECURE_GPT_API_VERSION: Optional[str] = None

    # APIM Configuration
    APIM_KEY: Optional[str] = None
    APIM_ONELOGIN_URL: Optional[str] = None
    APIM_BASE_URL: Optional[str] = None

    # Authentication
    AZURE_USE_AUTHENTICATION: bool = os.getenv("REQUIRE_AUTHENTICATION", "1") != "0"
    AZURE_SERVER_APP_ID: Optional[str] = None
    AZURE_SERVER_APP_SECRET: Optional[str] = None
    AZURE_CLIENT_APP_ID: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    TOKEN_CACHE_PATH: Optional[str] = None

    # Additional Authentication variables
    REQUIRE_AUTHENTICATION: int = 1
    APP_AUTHENTICATION_CLIENT_ID: Optional[str] = None

    # Knowledge Base Fields
    KB_FIELDS_CONTENT: str = "content"
    KB_FIELDS_SOURCEPAGE: str = "sourcepage"

    # Search Configuration
    AZURE_SEARCH_QUERY_LANGUAGE: str = "en-us"
    AZURE_SEARCH_QUERY_SPELLER: str = "lexicon"

    # Legacy API Keys (for fallback)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ORGANIZATION: Optional[str] = None
    STORAGE_CONNECTION_STRING: Optional[str] = None
    SEARCH_API_KEY: Optional[str] = None

    # Application Insights
    APPLICATIONINSIGHTS_CONNECTION_STRING: Optional[str] = None

    # CORS
    ALLOWED_ORIGIN: Optional[str] = None

    # Website Configuration
    WEBSITE_HOSTNAME: Optional[str] = None

    # Cosmos DB Configuration
    cosmos_db_endpoint: Optional[str] = None
    cosmos_db_key: Optional[str] = None
    cosmos_db_database_name: str = "hr_chatbot"
    cosmos_db_container_name: str = "chat_sessions"
    cosmos_db_partition_key: str = "/user_id"

    # MongoDB URL for Cosmos/MongoDB compatibility
    MONGODB_URL: Optional[str] = None

    # Development/Testing
    USE_MOCK_CLIENTS: bool = os.getenv("USE_MOCK_CLIENTS", "false").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
