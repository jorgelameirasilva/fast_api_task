"""
Client setup and dependency injection for Azure services and OpenAI.
This module follows FastAPI best practices for dependency injection.
"""

import os
from typing import Optional, Dict, Any
from functools import lru_cache
from loguru import logger

try:
    from dotenv import load_dotenv

    load_dotenv(".")
except ImportError:
    logger.warning("python-dotenv not installed, skipping .env file loading")

from app.core.config import settings

# Global clients - initialized during startup
_search_client = None
_openai_client = None
_blob_container_client = None
_auth_helper = None

# Configuration storage for approaches
CONFIG_OPENAI_CLIENT = "openai_client"
CONFIG_SEARCH_CLIENT = "search_client"
CONFIG_BLOB_CONTAINER_CLIENT = "blob_container_client"
CONFIG_AUTH_CLIENT = "auth_client"
CONFIG_ASK_APPROACH = "ask_approach"
CONFIG_CHAT_APPROACH = "chat_approach"

# Global configuration dict
current_app_config: Dict[str, Any] = {}


async def setup_clients():
    """
    Initialize and configure all Azure services and OpenAI clients.
    This function is called during FastAPI startup.
    """
    global _search_client, _openai_client, _blob_container_client, _auth_helper, current_app_config

    logger.info("Starting client setup...")

    # Setup Azure Search client
    _search_client = await _setup_search_client()

    # Setup Blob Storage client
    _blob_container_client = await _setup_blob_client()

    # Setup OpenAI client
    _openai_client = await _setup_openai_client()

    # Setup Authentication helper
    _auth_helper = await _setup_auth_helper()

    # Store clients in global config
    current_app_config[CONFIG_SEARCH_CLIENT] = _search_client
    current_app_config[CONFIG_OPENAI_CLIENT] = _openai_client
    current_app_config[CONFIG_BLOB_CONTAINER_CLIENT] = _blob_container_client
    current_app_config[CONFIG_AUTH_CLIENT] = _auth_helper

    # Setup approach configurations
    await _setup_approaches()

    logger.info("Client setup completed successfully")


async def _setup_search_client():
    """Setup Azure Search client"""
    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential

        if not settings.AZURE_SEARCH_SERVICE or not settings.SEARCH_API_KEY:
            logger.warning("Azure Search configuration missing, using mock client")
            return MockSearchClient()

        search_client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.AZURE_SEARCH_INDEX,
            credential=AzureKeyCredential(settings.SEARCH_API_KEY),
        )

        logger.info(
            f"Azure Search client configured for service: {settings.AZURE_SEARCH_SERVICE}"
        )
        return search_client

    except ImportError:
        logger.warning("Azure Search SDK not installed, using mock client")
        return MockSearchClient()
    except Exception as e:
        logger.error(f"Failed to setup Azure Search client: {e}")
        return MockSearchClient()


async def _setup_blob_client():
    """Setup Azure Blob Storage client"""
    try:
        from azure.storage.blob import BlobServiceClient

        if not settings.AZURE_STORAGE_ACCOUNT:
            logger.warning("Azure Storage configuration missing, using mock client")
            return MockBlobClient()

        if settings.STORAGE_CONNECTION_STRING:
            blob_service_client = BlobServiceClient.from_connection_string(
                settings.STORAGE_CONNECTION_STRING
            )
        else:
            blob_service_client = BlobServiceClient(
                account_url=settings.azure_storage_account_url,
                # Add credential here if needed
            )

        blob_container_client = blob_service_client.get_container_client(
            settings.AZURE_STORAGE_CONTAINER
        )

        logger.info(
            f"Azure Blob Storage client configured for account: {settings.AZURE_STORAGE_ACCOUNT}"
        )
        return blob_container_client

    except ImportError:
        logger.warning("Azure Storage SDK not installed, using mock client")
        return MockBlobClient()
    except Exception as e:
        logger.error(f"Failed to setup Azure Blob Storage client: {e}")
        return MockBlobClient()


async def _setup_openai_client():
    """Setup OpenAI client (Azure or OpenAI)"""
    try:
        if settings.OPENAI_HOST == "azure":
            return await _setup_azure_openai_client()
        else:
            return await _setup_standard_openai_client()

    except Exception as e:
        logger.error(f"Failed to setup OpenAI client: {e}")
        return MockOpenAIClient()


async def _setup_azure_openai_client():
    """Setup Azure OpenAI client"""
    try:
        from openai import AsyncAzureOpenAI
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        if not settings.AZURE_OPENAI_SERVICE:
            logger.warning("Azure OpenAI configuration missing, using mock client")
            return MockOpenAIClient()

        # Use managed identity authentication
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )

        openai_client = AsyncAzureOpenAI(
            api_version="2023-07-01-preview",
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=token_provider,
        )

        logger.info(
            f"Azure OpenAI client configured for service: {settings.AZURE_OPENAI_SERVICE}"
        )
        return openai_client

    except ImportError:
        logger.warning("Azure OpenAI SDK not installed, using mock client")
        return MockOpenAIClient()


async def _setup_standard_openai_client():
    """Setup standard OpenAI client"""
    try:
        from openai import AsyncOpenAI

        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key missing, using mock client")
            return MockOpenAIClient()

        openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            organization=settings.OPENAI_ORGANIZATION,
        )

        logger.info("Standard OpenAI client configured")
        return openai_client

    except ImportError:
        logger.warning("OpenAI SDK not installed, using mock client")
        return MockOpenAIClient()


async def _setup_auth_helper():
    """Setup authentication helper"""
    try:
        from app.core.auth import AuthenticationHelper

        if not settings.AZURE_USE_AUTHENTICATION:
            logger.info("Authentication disabled")
            return None

        auth_helper = AuthenticationHelper(
            use_authentication=settings.AZURE_USE_AUTHENTICATION,
            server_app_id=settings.AZURE_SERVER_APP_ID,
            server_app_secret=settings.AZURE_SERVER_APP_SECRET,
            client_app_id=settings.AZURE_CLIENT_APP_ID,
            tenant_id=settings.AZURE_TENANT_ID,
            token_cache_path=settings.TOKEN_CACHE_PATH,
        )

        logger.info("Authentication helper configured")
        return auth_helper

    except ImportError:
        logger.warning("Authentication helper not available")
        return None
    except Exception as e:
        logger.error(f"Failed to setup authentication helper: {e}")
        return None


async def _setup_approaches():
    """Setup approach configurations"""
    try:
        from app.approaches import (
            RetrieveThenReadApproach,
            ChatReadRetrieveReadApproach,
        )
        from app.approaches.approach_registry import register_approach_instance

        # Setup RetrieveThenRead approach
        ask_approach = RetrieveThenReadApproach(
            search_client=_search_client,
            openai_client=_openai_client,
            chatgpt_model=settings.OPENAI_CHATGPT_MODEL,
            chatgpt_deployment=settings.AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            embedding_model=settings.OPENAI_EMB_MODEL,
            embedding_deployment=settings.AZURE_OPENAI_EMB_DEPLOYMENT,
            sourcepage_field=settings.KB_FIELDS_SOURCEPAGE,
            content_field=settings.KB_FIELDS_CONTENT,
            query_language=settings.AZURE_SEARCH_QUERY_LANGUAGE,
            query_speller=settings.AZURE_SEARCH_QUERY_SPELLER,
        )

        # Setup ChatReadRetrieveRead approach
        chat_approach = ChatReadRetrieveReadApproach(
            search_client=_search_client,
            openai_client=_openai_client,
            chatgpt_model=settings.OPENAI_CHATGPT_MODEL,
            chatgpt_deployment=settings.AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            embedding_model=settings.OPENAI_EMB_MODEL,
            embedding_deployment=settings.AZURE_OPENAI_EMB_DEPLOYMENT,
            sourcepage_field=settings.KB_FIELDS_SOURCEPAGE,
            content_field=settings.KB_FIELDS_CONTENT,
            query_language=settings.AZURE_SEARCH_QUERY_LANGUAGE,
            query_speller=settings.AZURE_SEARCH_QUERY_SPELLER,
        )

        # Register approaches with the global registry (this replaces class-based instances)
        register_approach_instance("retrieve_then_read", ask_approach)
        register_approach_instance("chat_read_retrieve_read", chat_approach)

        # Store approaches in global config for backward compatibility
        current_app_config[CONFIG_ASK_APPROACH] = ask_approach
        current_app_config[CONFIG_CHAT_APPROACH] = chat_approach

        logger.info(
            "Approach configurations completed and registered with dependency injection"
        )

    except Exception as e:
        logger.error(f"Failed to setup approaches: {e}")
        logger.warning("Falling back to class-based approach instantiation")


# Dependency injection functions
@lru_cache()
def get_search_client():
    """Get the configured search client"""
    return current_app_config.get(CONFIG_SEARCH_CLIENT)


@lru_cache()
def get_openai_client():
    """Get the configured OpenAI client"""
    return current_app_config.get(CONFIG_OPENAI_CLIENT)


@lru_cache()
def get_blob_client():
    """Get the configured blob storage client"""
    return current_app_config.get(CONFIG_BLOB_CONTAINER_CLIENT)


@lru_cache()
def get_auth_helper():
    """Get the configured authentication helper"""
    return current_app_config.get(CONFIG_AUTH_CLIENT)


def get_app_config(key: str, default=None):
    """Get a configuration value"""
    return current_app_config.get(key, default)


# Mock clients for development/testing
class MockSearchClient:
    """Mock search client for development"""

    async def search(self, *args, **kwargs):
        return []

    def close(self):
        pass


class MockBlobClient:
    """Mock blob client for development"""

    async def list_blobs(self, *args, **kwargs):
        return []

    def close(self):
        pass


class MockOpenAIClient:
    """Mock OpenAI client for development"""

    class Chat:
        class Completions:
            async def create(self, *args, **kwargs):
                return {"choices": [{"message": {"content": "Mock response"}}]}

    class Embeddings:
        async def create(self, *args, **kwargs):
            return {"data": [{"embedding": [0.1] * 1536}]}

    def __init__(self):
        self.chat = self.Chat()
        self.chat.completions = self.Chat.Completions()
        self.embeddings = self.Embeddings()

    def close(self):
        pass


async def cleanup_clients():
    """Cleanup clients during shutdown"""
    global _search_client, _openai_client, _blob_container_client

    logger.info("Cleaning up clients...")

    try:
        if _search_client and hasattr(_search_client, "close"):
            _search_client.close()

        if _openai_client and hasattr(_openai_client, "close"):
            await _openai_client.close()

        if _blob_container_client and hasattr(_blob_container_client, "close"):
            _blob_container_client.close()

    except Exception as e:
        logger.error(f"Error during client cleanup: {e}")

    logger.info("Client cleanup completed")
