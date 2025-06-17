"""
Chat Service - Handles chat business logic following SOLID principles
Single Responsibility: Manage chat approach and process chat requests
"""

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
    """
    Chat service following SOLID principles
    Single Responsibility: Manage chat approach and process requests
    """

    def __init__(self):
        self.approach = None
        self._setup_approach()

    def _setup_approach(self):
        """Setup the chat approach with appropriate clients"""
        try:
            # Get clients based on configuration
            search_client, openai_client = self._get_clients()

            # Initialize approach
            self.approach = self._create_approach(search_client, openai_client)

            logger.info("Chat approach initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup chat approach: {str(e)}")
            raise

    def _get_clients(self):
        """Get appropriate clients based on configuration"""
        if settings.use_mock_clients or settings.debug:
            return get_mock_search_client(), get_mock_openai_client()
        else:
            raise NotImplementedError(
                "Production clients not implemented yet - use mock clients"
            )

    def _create_approach(self, search_client, openai_client):
        """Create and configure the chat approach"""
        from app.approaches.chatreadretrieveread import ChatReadRetrieveReadApproach

        return ChatReadRetrieveReadApproach(
            search_client=search_client,
            openai_client=openai_client,
            chatgpt_model=settings.secure_gpt_deployment_id
            or settings.azure_openai_chatgpt_model
            or "gpt-4o",
            chatgpt_deployment=settings.azure_openai_chatgpt_deployment,
            embedding_model=settings.secure_gpt_emb_deployment_id
            or settings.azure_openai_emb_model_name
            or "text-embedding-ada-002",
            embedding_deployment=settings.azure_openai_emb_deployment,
            sourcepage_field=settings.kb_fields_sourcepage,
            content_field=settings.kb_fields_content,
            query_language=settings.azure_search_query_language,
            query_speller=settings.azure_search_query_speller,
        )

    async def process_chat(
        self, request, context: dict[str, Any]
    ) -> dict[str, Any] | AsyncGenerator[dict[str, Any], None]:
        """
        Process chat request using the configured approach
        Returns either a dict (non-streaming) or AsyncGenerator (streaming)
        """
        if not self.approach:
            raise Exception("Chat approach not initialized")

        # Convert request to approach format
        messages = self._convert_messages(request.messages)

        # Call approach
        return await self.approach.run(
            messages,
            stream=request.stream,
            context=context,
            session_state=request.session_state,
        )

    def _convert_messages(self, messages):
        """Convert request messages to approach format"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]


# Global instance
chat_service = ChatService()
