"""
Setup module for chat approaches and clients
"""

import logging
import os
import httpx
from typing import Optional
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import (
    DefaultAzureCredential,
    ClientSecretCredential,
    get_bearer_token_provider,
)
from azure.storage.blob import BlobServiceClient as SyncBlobServiceClient
from openai import AsyncOpenAI, AsyncAzureOpenAI

# Optional OpenTelemetry imports for monitoring
try:
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    # OpenTelemetry not available - running in test mode
    configure_azure_monitor = None
    AioHttpClientInstrumentor = None
    FastAPIInstrumentor = None
    HTTPXClientInstrumentor = None
    OPENTELEMETRY_AVAILABLE = False

from app.core.config import settings
from app.core.identity import OneAccount
from app.utils.mock_clients import (
    get_mock_search_client,
    get_mock_openai_client,
    get_mock_table_service_client,
)

logger = logging.getLogger(__name__)

# Global approach instance
_chat_approach = None
# Global table service client instance
_table_service_client = None


def get_table_service_client():
    """Get or create the table service client instance"""
    global _table_service_client

    if _table_service_client is None:
        logger.info("Creating table service client instance")
        if settings.USE_MOCK_CLIENTS:
            _table_service_client = get_mock_table_service_client()
        else:
            _table_service_client = _get_azure_table_service_client()

    return _table_service_client


def get_chat_approach():
    """Get or create the chat approach instance"""
    global _chat_approach

    if _chat_approach is None:
        _chat_approach = _create_chat_approach()

    return _chat_approach


def get_blob_client_for_logging():
    """Create blob client specifically for logging (sync version)"""
    # Only create blob client in production
    if not settings.WEBSITE_HOSTNAME:
        raise Exception("Blob client not available in development mode")

    try:
        blob_service_client = SyncBlobServiceClient(
            account_url=f"https://{settings.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
            credential=ClientSecretCredential(
                client_id=settings.AZURE_STORAGE_CLIENT_ID,
                client_secret=settings.AZURE_STORAGE_CLIENT_SECRET,
                tenant_id=settings.AZURE_SEARCH_TENANT_ID,
            ),
        )
        blob_container_client = blob_service_client.get_container_client(
            settings.AZURE_STORAGE_CONTAINER
        )
        return blob_container_client

    except Exception as e:
        logger.error(f"Failed to initialize blob client for logging: {str(e)}")
        raise


def _create_chat_approach():
    """Create and configure the chat approach"""
    try:
        # Get clients based on configuration
        search_client, openai_client, embeddings_client, table_service_client = (
            _get_clients()
        )

        # Initialize approach
        from app.approaches.chatreadretrieveread import ChatReadRetrieveReadApproach

        # Use the same model selection logic as old app.py
        chatgpt_model = settings.SECURE_GPT_DEPLOYMENT_ID
        embedding_model = settings.SECURE_GPT_EMB_DEPLOYMENT_ID

        approach = ChatReadRetrieveReadApproach(
            search_client=search_client,
            openai_client=openai_client,
            embeddings_client=embeddings_client,
            chatgpt_model=chatgpt_model,
            chatgpt_deployment=settings.AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            embedding_model=embedding_model,
            embedding_deployment=settings.AZURE_OPENAI_EMB_DEPLOYMENT,
            sourcepage_field=settings.KB_FIELDS_SOURCEPAGE,
            content_field=settings.KB_FIELDS_CONTENT,
            query_language=settings.AZURE_SEARCH_QUERY_LANGUAGE,
            query_speller=settings.AZURE_SEARCH_QUERY_SPELLER,
        )

        logger.info("Chat approach initialized successfully")
        return approach

    except Exception as e:
        logger.error(f"Failed to setup chat approach: {str(e)}")
        raise


def _get_clients():
    """Get appropriate clients based on configuration"""
    if settings.USE_MOCK_CLIENTS:
        logger.info("Using mock clients for testing")
        return (
            get_mock_search_client(),
            get_mock_openai_client(),
            get_mock_openai_client(),
            get_mock_table_service_client(),
        )
    else:
        logger.info("Initializing production Azure clients")
        search_client = _get_azure_search_client()
        openai_client = _get_azure_openai_client()
        embeddings_client = _get_azure_embeddings_client()
        table_service_client = _get_azure_table_service_client()
        return search_client, openai_client, embeddings_client, table_service_client


def _get_azure_search_client() -> SearchClient:
    """Create Azure Search client exactly like old app.py"""
    try:
        # Use ClientSecretCredential exactly like old app.py
        search_client = SearchClient(
            endpoint=f"https://{settings.AZURE_SEARCH_SERVICE}.search.windows.net",
            index_name=settings.AZURE_SEARCH_INDEX,
            credential=ClientSecretCredential(
                tenant_id=settings.AZURE_SEARCH_TENANT_ID,
                client_id=settings.AZURE_SEARCH_CLIENT_ID,
                client_secret=settings.AZURE_SEARCH_CLIENT_SECRET,
            ),
        )

        logger.info(
            f"Azure Search client initialized for service: {settings.AZURE_SEARCH_SERVICE}"
        )
        return search_client

    except Exception as e:
        logger.error(f"Failed to initialize Azure Search client: {str(e)}")
        raise


def _get_azure_openai_client() -> AsyncOpenAI:
    """Create Azure OpenAI client exactly like old app.py with APIM and SecureGPT"""
    try:
        # Build APIM URLs exactly like old app.py
        APIM_COMPLETIONS_URL = (
            f"{settings.APIM_BASE_URL}/{settings.SECURE_GPT_DEPLOYMENT_ID}"
        )

        # Use AsyncAzureOpenAI with APIM and OneAccount exactly like old app.py
        openai_client = AsyncAzureOpenAI(
            base_url=APIM_COMPLETIONS_URL,
            azure_ad_token_provider=get_bearer_token_provider(
                OneAccount(
                    settings.SECURE_GPT_CLIENT_ID,
                    settings.SECURE_GPT_CLIENT_SECRET,
                    settings.APIM_KEY,
                    settings.APIM_ONELOGIN_URL,
                )
            ),
            api_version=settings.SECURE_GPT_API_VERSION,
            http_client=httpx.AsyncClient(verify=False),
            default_headers={"Ocp-Apim-Subscription-Key": settings.APIM_KEY},
        )

        logger.info(
            f"Azure OpenAI client initialized with APIM: {settings.APIM_BASE_URL}"
        )
        return openai_client

    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
        raise


def _get_azure_embeddings_client() -> AsyncOpenAI:
    """Create Azure OpenAI embeddings client exactly like old app.py"""
    try:
        # Build APIM embeddings URL exactly like old app.py
        APIM_EMBEDDINGS_URL = (
            f"{settings.APIM_BASE_URL}/{settings.SECURE_GPT_EMB_DEPLOYMENT_ID}"
        )

        # Use AsyncAzureOpenAI with APIM and OneAccount exactly like old app.py
        embeddings_client = AsyncAzureOpenAI(
            base_url=APIM_EMBEDDINGS_URL,
            azure_ad_token_provider=get_bearer_token_provider(
                OneAccount(
                    settings.SECURE_GPT_CLIENT_ID,
                    settings.SECURE_GPT_CLIENT_SECRET,
                    settings.APIM_KEY,
                    settings.APIM_ONELOGIN_URL,
                )
            ),
            api_version=settings.SECURE_GPT_API_VERSION,
            http_client=httpx.AsyncClient(verify=False),
            default_headers={"Ocp-Apim-Subscription-Key": settings.APIM_KEY},
        )

        logger.info(
            f"Azure OpenAI embeddings client initialized with APIM: {settings.APIM_BASE_URL}"
        )
        return embeddings_client

    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI embeddings client: {str(e)}")
        raise


def _get_azure_table_service_client():
    """Create Azure Storage Table service client for production"""
    try:
        # For now, use mock client even in production since Azure Storage Table package is not installed
        # This prevents import errors while maintaining functionality
        logger.info(
            "Azure Storage Table client not implemented yet - using mock client"
        )
        return get_mock_table_service_client()

        # TODO: Implement real Azure Storage Table client when needed
        # from azure.data.tables.aio import TableServiceClient
        # from azure.identity import ClientSecretCredential
        #
        # credential = ClientSecretCredential(
        #     tenant_id=settings.AZURE_SEARCH_TENANT_ID,
        #     client_id=settings.AZURE_STORAGE_CLIENT_ID,
        #     client_secret=settings.AZURE_STORAGE_CLIENT_SECRET,
        # )
        #
        # endpoint = f"https://{settings.AZURE_STORAGE_ACCOUNT}.table.core.windows.net"
        # table_service_client = TableServiceClient(endpoint=endpoint, credential=credential)
        #
        # logger.info(f"Azure Storage Table client initialized: {endpoint}")
        # return table_service_client

    except Exception as e:
        logger.error(f"Failed to initialize Azure Storage Table client: {str(e)}")
        raise


def setup_monitoring(app):
    """Configure Application Insights monitoring"""
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("OpenTelemetry not available - monitoring disabled")
        return

    try:
        logger.info("Configuring Application Insights monitoring")
        configure_azure_monitor()

        # This tracks HTTP requests made by aiohttp:
        AioHttpClientInstrumentor().instrument()

        # This tracks HTTP requests made by httpx/openai:
        HTTPXClientInstrumentor().instrument()

        # This instruments FastAPI requests:
        FastAPIInstrumentor.instrument_app(app)

        logger.info("Application Insights monitoring configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure Application Insights monitoring: {e}")
        raise
