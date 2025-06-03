from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from app.schemas.chat import AskRequest, AskResponse
from app.services.response_generator import ResponseGenerator


class AskService:
    """Service focused solely on ask operations"""

    def __init__(self, response_generator: ResponseGenerator = None):
        self.response_generator = response_generator or ResponseGenerator()

    async def process_ask(
        self, request: AskRequest, stream: bool = False
    ) -> AskResponse:
        """Process an ask request - simple processing"""
        logger.info(f"Processing ask request: {request.user_query[:50]}...")

        try:
            # Generate response using the response generator
            response_content = await self.response_generator.generate_ask_response(
                request.user_query
            )

            # Get relevant sources
            sources = await self.response_generator.get_relevant_sources(
                request.user_query
            )

            # Build response context
            response_context = {
                "streaming": stream,
                "query_processed_at": datetime.now().isoformat(),
            }

            return AskResponse(
                user_query=request.user_query,
                chatbot_response=response_content,
                context=response_context,
                sources=sources,
                count=request.count or 0,
            )

        except Exception as e:
            logger.error(f"Error processing ask request: {e}")
            return self._build_fallback_response(request)

    def _build_fallback_response(self, request: AskRequest) -> AskResponse:
        """Build fallback response when processing fails"""
        logger.warning("Using fallback response for ask request")

        fallback_response = (
            f"I apologize, but I encountered an issue while processing your question: "
            f"'{request.user_query}'. Please try rephrasing your question or contact support."
        )

        return AskResponse(
            user_query=request.user_query,
            chatbot_response=fallback_response,
            context={
                "error": "ask_processing_failed",
                "fallback_used": True,
                "query_processed_at": datetime.now().isoformat(),
            },
            sources=[],
            count=request.count or 0,
        )


# Create service instance
ask_service = AskService()
