"""
Setup module for chat approaches and clients
"""

import logging
from typing import Optional

from app.core.config import settings
from app.utils.mock_clients import (
    get_mock_search_client,
    get_mock_openai_client,
)

logger = logging.getLogger(__name__)

# Global approach instance
_chat_approach = None


def get_chat_approach():
    """Get or create the chat approach instance"""
    global _chat_approach

    if _chat_approach is None:
        _chat_approach = _create_chat_approach()

    return _chat_approach


def _create_chat_approach():
    """Create and configure the chat approach"""
    try:
        # Get clients based on configuration
        search_client, openai_client = _get_clients()

        # Initialize approach
        from app.approaches.chatreadretrieveread import ChatReadRetrieveReadApproach

        approach = ChatReadRetrieveReadApproach(
            search_client=search_client,
            openai_client=openai_client,
            chatgpt_model=settings.SECURE_GPT_DEPLOYMENT_ID
            or settings.AZURE_OPENAI_CHATGPT_MODEL
            or "gpt-4o",
            chatgpt_deployment=settings.AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            embedding_model=settings.SECURE_GPT_EMB_DEPLOYMENT_ID
            or settings.AZURE_OPENAI_EMB_MODEL_NAME
            or "text-embedding-ada-002",
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
    if settings.USE_MOCK_CLIENTS or settings.debug:
        return get_mock_search_client(), get_mock_openai_client()
    else:
        raise NotImplementedError(
            "Production clients not implemented yet - use mock clients"
        )
