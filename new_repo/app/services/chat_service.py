"""Chat service for handling chat business logic - Simplified design"""

import logging
from typing import Any
from collections.abc import AsyncGenerator

from app.core.config import settings
from app.utils.mock_clients import (
    get_mock_search_client,
    get_mock_openai_client,
)

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat interactions - Simplified to match old design"""

    def __init__(self):
        self.approach = None
        self._setup_approach()

    def _setup_approach(self):
        """Setup the chat approach with clients"""
        try:
            # Use mock clients for development/testing
            if settings.use_mock_clients or settings.debug:
                search_client = get_mock_search_client()
                openai_client = get_mock_openai_client()
            else:
                # In production, you would initialize real clients here
                raise NotImplementedError(
                    "Production clients not implemented yet - use mock clients"
                )

            # Import and setup the exact same approach as original
            from app.approaches.chatreadretrieveread import ChatReadRetrieveReadApproach

            self.approach = ChatReadRetrieveReadApproach(
                search_client=search_client,
                openai_client=openai_client,
                chatgpt_model=settings.secure_gpt_deployment_id
                or settings.azure_openai_chatgpt_model
                or "gpt-4o",  # Fallback for testing
                chatgpt_deployment=settings.azure_openai_chatgpt_deployment,
                embedding_model=settings.secure_gpt_emb_deployment_id
                or settings.azure_openai_emb_model_name
                or "text-embedding-ada-002",  # Fallback for testing
                embedding_deployment=settings.azure_openai_emb_deployment,
                sourcepage_field=settings.kb_fields_sourcepage,
                content_field=settings.kb_fields_content,
                query_language=settings.azure_search_query_language,
                query_speller=settings.azure_search_query_speller,
            )

            logger.info("Chat approach initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup chat approach: {str(e)}")
            raise

    async def process_chat_simple(
        self, request, context: dict[str, Any]
    ) -> dict[str, Any] | AsyncGenerator[dict[str, Any], None]:
        """
        Simple chat processing - just call the approach directly like the old design

        The approach handles streaming vs non-streaming automatically in its run() method
        """
        if not self.approach:
            raise Exception("Chat approach not initialized")

        # Convert messages to the format expected by approaches
        messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        # Call approach directly - it handles streaming/non-streaming
        result = await self.approach.run(
            messages,
            stream=request.stream,
            context=context,
            session_state=request.session_state,
        )

        return result

    async def process_chat_with_session(
        self, request, context: dict[str, Any], session_id: str
    ) -> dict[str, Any] | AsyncGenerator[dict[str, Any], None]:
        """
        Chat processing with session - also simplified
        """
        if not self.approach:
            raise Exception("Chat approach not initialized")

        # Convert messages to the format expected by approaches
        messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        # Call approach directly with session_id
        result = await self.approach.run(
            messages,
            stream=request.stream,
            context=context,
            session_state=session_id,
        )

        return result


# Global instance
chat_service = ChatService()
