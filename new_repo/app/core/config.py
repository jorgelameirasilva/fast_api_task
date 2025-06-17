import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App Configuration
    app_name: str = "HR Chatbot API"
    debug: bool = False

    # Azure Storage
    azure_storage_account: str = "stdiagnosticsstorageprod"
    azure_storage_container: str = "s-alt-0303-asia-or-us3-dlc13-webintelligentchatbot"
    azure_storage_client_id: Optional[str] = None
    azure_storage_client_secret: Optional[str] = None

    # Azure Search
    azure_search_service: Optional[str] = None
    azure_search_index: Optional[str] = None
    azure_search_client_id: Optional[str] = None
    azure_search_client_secret: Optional[str] = None
    azure_search_tenant_id: Optional[str] = None

    # OpenAI Configuration
    openai_host: str = "azure"
    azure_openai_chatgpt_model: str = "gpt-40"
    azure_openai_emb_model_name: str = "text-embedding-ada-002"
    azure_openai_service: str = "saic-azu-eus2-npd-openaioc-specialservices"
    azure_openai_chatgpt_deployment: str = "gpt-4o-chatbot-poc"
    azure_openai_emb_deployment: str = "embeddings"

    # Secure GPT Configuration
    secure_gpt_deployment_id: Optional[str] = None
    secure_gpt_emb_deployment_id: Optional[str] = None
    secure_gpt_client_id: Optional[str] = None
    secure_gpt_client_secret: Optional[str] = None
    secure_gpt_api_version: Optional[str] = None

    # APIM Configuration
    apim_key: Optional[str] = None
    apim_onelogin_url: Optional[str] = None
    apim_base_url: Optional[str] = None

    # Authentication
    azure_use_authentication: bool = True
    azure_server_app_id: Optional[str] = None
    azure_server_app_secret: Optional[str] = None
    azure_client_app_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    token_cache_path: Optional[str] = None

    # Knowledge Base Fields
    kb_fields_content: str = "content"
    kb_fields_sourcepage: str = "sourcepage"

    # Search Configuration
    azure_search_query_language: str = "en-us"
    azure_search_query_speller: str = "lexicon"

    # Legacy API Keys (for fallback)
    openai_api_key: Optional[str] = None
    openai_organization: Optional[str] = None
    storage_connection_string: Optional[str] = None
    search_api_key: Optional[str] = None

    # Application Insights
    applicationinsights_connection_string: Optional[str] = None

    # CORS
    allowed_origin: Optional[str] = None

    # Cosmos DB Configuration
    cosmos_db_endpoint: Optional[str] = None
    cosmos_db_key: Optional[str] = None
    cosmos_db_database_name: str = "hr_chatbot"
    cosmos_db_container_name: str = "chat_sessions"
    cosmos_db_partition_key: str = "/user_id"

    # Development/Testing
    use_mock_clients: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
