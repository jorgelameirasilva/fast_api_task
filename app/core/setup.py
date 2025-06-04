"""
Client setup and dependency injection for Azure services and OpenAI.
This module follows FastAPI best practices for dependency injection.
"""

import os
from functools import lru_cache
from loguru import logger

from app.core.config import settings

# Global configuration storage
current_app_config = {}

# Configuration keys
CONFIG_SEARCH_CLIENT = "search_client"
CONFIG_OPENAI_CLIENT = "openai_client"
CONFIG_BLOB_CONTAINER_CLIENT = "blob_container_client"
CONFIG_AUTH_CLIENT = "auth_client"
CONFIG_ASK_APPROACH = "ask_approach"
CONFIG_CHAT_APPROACH = "chat_approach"

# Global clients
_search_client = None
_openai_client = None
_blob_container_client = None
_auth_helper = None


async def setup_clients():
    """Setup application clients and approaches"""
    global _search_client, _openai_client, _blob_container_client, _auth_helper

    logger.info("Starting client setup...")

    try:
        # Setup clients first
        _search_client = await _setup_search_client()
        _blob_container_client = await _setup_blob_client()
        _openai_client = await _setup_openai_client()
        _auth_helper = await _setup_auth_helper()

        # Store in global config
        current_app_config[CONFIG_SEARCH_CLIENT] = _search_client
        current_app_config[CONFIG_OPENAI_CLIENT] = _openai_client
        current_app_config[CONFIG_BLOB_CONTAINER_CLIENT] = _blob_container_client
        current_app_config[CONFIG_AUTH_CLIENT] = _auth_helper

        logger.info("Basic client setup completed successfully")

    except Exception as e:
        logger.error(f"Error during basic client setup: {e}")
        # Use mock clients as fallback
        _search_client = MockSearchClient()
        _openai_client = MockOpenAIClient()
        _blob_container_client = MockBlobClient()

        current_app_config[CONFIG_SEARCH_CLIENT] = _search_client
        current_app_config[CONFIG_OPENAI_CLIENT] = _openai_client
        current_app_config[CONFIG_BLOB_CONTAINER_CLIENT] = _blob_container_client
        current_app_config[CONFIG_AUTH_CLIENT] = None

        logger.warning("Using mock clients due to setup errors")

    # Always setup approaches (critical for API functionality)
    try:
        approach_setup_success = await _setup_approaches()
        if approach_setup_success:
            logger.info("Approach setup completed successfully")
        else:
            logger.warning("Approach setup completed with fallbacks")

    except Exception as e:
        logger.critical(f"CRITICAL: Failed to setup approaches: {e}")
        # This should cause startup to fail if approaches cannot be initialized
        raise RuntimeError(
            f"Could not initialize approaches - system cannot start: {e}"
        )

    logger.info("Client and approach setup completed")


async def _setup_search_client():
    """Setup Azure Search client"""
    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential

        if not all([settings.AZURE_SEARCH_SERVICE, settings.SEARCH_API_KEY]):
            logger.warning("Azure Search configuration missing, using mock client")
            return MockSearchClient()

        search_client = SearchClient(
            endpoint=f"https://{settings.AZURE_SEARCH_SERVICE}.search.windows.net",
            index_name=settings.AZURE_SEARCH_INDEX,
            credential=AzureKeyCredential(settings.SEARCH_API_KEY),
        )

        logger.info("Azure Search client configured")
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

        if not settings.STORAGE_CONNECTION_STRING:
            logger.warning("Azure Storage configuration missing, using mock client")
            return MockBlobClient()

        blob_client = BlobServiceClient(
            account_url=f"https://{settings.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
            container_name="aisearch",
            credentials=settings.STORAGE_CONNECTION_STRING,
        )
        blob_container_client = blob_client.get_container_client(
            settings.AZURE_STORAGE_CONTAINER
        )

        logger.info("Azure Blob Storage client configured")
        return blob_container_client

    except ImportError:
        logger.warning("Azure Storage SDK not installed, using mock client")
        return MockBlobClient()
    except Exception as e:
        logger.error(f"Failed to setup Azure Blob Storage client: {e}")
        return MockBlobClient()


async def _setup_openai_client():
    """Setup OpenAI client (Azure or Standard)"""
    if settings.OPENAI_HOST == "azure":
        return await _setup_azure_openai_client()
    else:
        return await _setup_standard_openai_client()


async def _setup_azure_openai_client():
    """Setup Azure OpenAI client"""
    try:
        from openai import AsyncAzureOpenAI

        if not all([settings.AZURE_OPENAI_SERVICE, settings.OPENAI_API_KEY]):
            logger.warning("Azure OpenAI configuration missing, using mock client")
            return MockOpenAIClient()

        openai_client = AsyncAzureOpenAI(
            api_version="2023-07-01-preview",
            azure_endpoint=f"https://{settings.AZURE_OPENAI_SERVICE}.openai.azure.com",
            api_key=settings.OPENAI_API_KEY,
        )

        logger.info("Azure OpenAI client configured")
        return openai_client

    except ImportError:
        logger.warning("Azure OpenAI SDK not installed, using mock client")
        return MockOpenAIClient()
    except Exception as e:
        logger.error(f"Failed to setup Azure OpenAI client: {e}")
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
    if not settings.AZURE_USE_AUTHENTICATION:
        logger.info("Authentication disabled")
        return None

    try:
        from app.core.auth import AuthenticationHelper

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
    """Setup approach configurations - ensure approaches are always available"""
    try:
        from app.approaches import (
            RetrieveThenReadApproach,
            ChatReadRetrieveReadApproach,
        )
        from app.approaches.approach_registry import register_approach_instance

        # Always setup approaches with the best available clients
        # This ensures approaches work even with mock clients for development
        logger.info("Setting up approach configurations...")

        # Setup RetrieveThenRead approach (for /ask endpoint)
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

        # Setup ChatReadRetrieveRead approach (for /chat endpoint)
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

        # Register approaches with the global registry
        register_approach_instance("retrieve_then_read", ask_approach)
        register_approach_instance("chat_read_retrieve_read", chat_approach)

        # Store approaches in global config (matching old code structure)
        current_app_config[CONFIG_ASK_APPROACH] = ask_approach
        current_app_config[CONFIG_CHAT_APPROACH] = chat_approach

        # Log successful setup
        logger.info(f"Ask approach configured: {ask_approach.__class__.__name__}")
        logger.info(f"Chat approach configured: {chat_approach.__class__.__name__}")
        logger.info(
            "Approach configurations completed and registered with dependency injection"
        )

        return True

    except Exception as e:
        logger.error(f"Failed to setup approaches: {e}")
        # This is critical - approaches should always be available
        logger.error(
            "CRITICAL: Approach setup failed - API will not function correctly"
        )

        # Try to create minimal approaches as last resort
        try:
            logger.warning("Attempting to create minimal fallback approaches...")

            from app.approaches import (
                RetrieveThenReadApproach,
                ChatReadRetrieveReadApproach,
            )

            # Create minimal approaches without clients
            minimal_ask_approach = RetrieveThenReadApproach()
            minimal_chat_approach = ChatReadRetrieveReadApproach()

            current_app_config[CONFIG_ASK_APPROACH] = minimal_ask_approach
            current_app_config[CONFIG_CHAT_APPROACH] = minimal_chat_approach

            logger.warning("Minimal fallback approaches created")
            return False

        except Exception as fallback_error:
            logger.critical(
                f"Failed to create even minimal approaches: {fallback_error}"
            )
            # This should never happen in normal operation
            raise RuntimeError(
                "Could not initialize any approaches - system cannot start"
            )


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


@lru_cache()
def get_ask_approach():
    """Get the configured ask approach"""
    return current_app_config.get(CONFIG_ASK_APPROACH)


@lru_cache()
def get_chat_approach():
    """Get the configured chat approach"""
    return current_app_config.get(CONFIG_CHAT_APPROACH)


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
    """Simple mock OpenAI client that returns real OpenAI types"""

    class Chat:
        class Completions:
            async def create(self, messages=None, model="gpt-3.5-turbo", **kwargs):
                from openai.types.chat import ChatCompletion, ChatCompletionMessage
                from openai.types.chat.chat_completion import Choice
                from openai.types.completion_usage import CompletionUsage
                import time
                import uuid

                content = f"Based on the conversation context and retrieved documents, here's the answer using the Chat-Read-Retrieve-Read approach."

                message = ChatCompletionMessage(content=content, role="assistant")
                message.context = {
                    "data_points": ["Mock document 1", "Mock document 2"],
                    "thoughts": "Mock analysis and reasoning",
                    "followup_questions": ["<<Question 1?>>", "<<Question 2?>>"],
                }

                return ChatCompletion(
                    id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                    choices=[Choice(finish_reason="stop", index=0, message=message)],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion",
                    usage=CompletionUsage(
                        completion_tokens=20, prompt_tokens=10, total_tokens=30
                    ),
                )

    class Embeddings:
        async def create(self, input=None, model="text-embedding-ada-002", **kwargs):
            from openai.types import CreateEmbeddingResponse, Embedding
            from openai.types.create_embedding_response import Usage

            return CreateEmbeddingResponse(
                object="list",
                data=[Embedding(object="embedding", index=0, embedding=[0.1] * 1536)],
                model=model,
                usage=Usage(prompt_tokens=5, total_tokens=5),
            )

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
