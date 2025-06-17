"""
Chat Orchestrator - Orchestrates chat requests following SOLID principles
Single Responsibility: Coordinates between services and handles response formatting
"""

import logging
import json
from typing import Any
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest
from app.services.chat_service import chat_service
from app.services.session_manager import SessionManager
from app.utils import make_json_serializable

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """
    Orchestrates chat requests following SOLID principles
    Single Responsibility: Coordinate chat processing and response formatting
    """

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    async def process_chat_request(
        self, request: ChatRequest, current_user: dict[str, Any]
    ):
        """
        Process chat request - orchestrates the flow
        Returns appropriate StreamingResponse for both streaming and non-streaming
        """
        try:
            logger.info(f"Chat request from user: {current_user.get('oid', 'unknown')}")

            # Prepare context
            context = self._prepare_context(request, current_user)

            # Get result from chat service
            result = await chat_service.process_chat(request, context)

            # Format and return response
            return self._format_response(result)

        except Exception as e:
            logger.error(f"Chat processing failed: {str(e)}")
            raise

    def _prepare_context(
        self, request: ChatRequest, current_user: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepare context for chat processing"""
        context = request.context.copy() if request.context else {}
        context["auth_claims"] = current_user
        return context

    def _format_response(self, result) -> StreamingResponse:
        """Format result as NDJSON streaming response"""
        if isinstance(result, dict):
            # Non-streaming: convert to single NDJSON line
            return self._format_dict_response(result)
        else:
            # Streaming: format as NDJSON
            return self._format_stream_response(result)

    def _format_dict_response(self, result: dict) -> StreamingResponse:
        """Format dict result as single NDJSON line"""
        serializable_result = make_json_serializable(result)

        async def generate_single():
            yield f"data: {json.dumps(serializable_result)}\n\n"

        return StreamingResponse(generate_single(), media_type="application/json-lines")

    def _format_stream_response(self, result) -> StreamingResponse:
        """Format streaming result as NDJSON"""

        async def serialize_and_format():
            async for chunk in result:
                serialized_chunk = make_json_serializable(chunk)
                yield f"data: {json.dumps(serialized_chunk, default=str)}\n\n"

        return StreamingResponse(
            serialize_and_format(), media_type="application/json-lines"
        )


# Global instance
from app.services.session_manager import session_manager

chat_orchestrator = ChatOrchestrator(session_manager=session_manager)
