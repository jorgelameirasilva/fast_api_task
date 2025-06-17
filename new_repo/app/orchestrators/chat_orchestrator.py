"""
Chat Orchestrator - Simplified to match old design

Coordinates chat processing by calling the approach directly.
The approach handles streaming vs non-streaming automatically.
"""

import json
import logging
from typing import Any
from collections.abc import AsyncGenerator
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse, ChatChoice, ChatMessage
from app.services.chat_service import chat_service
from app.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """
    Simplified orchestrator that calls approach directly like the old design
    """

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)

    async def process_chat_request(
        self, request: ChatRequest, current_user: dict[str, Any]
    ) -> StreamingResponse:
        """
        Process a chat request - simplified to match old design
        """
        user_id = current_user.get("oid", "unknown")

        try:
            self.logger.info(f"Processing chat request for user: {user_id}")

            # Prepare context like the old design
            context = request.context.copy() if request.context else {}
            context["auth_claims"] = current_user

            # Call the approach directly - it handles streaming/non-streaming
            result = await chat_service.process_chat_simple(request, context)

            # Convert result to streaming response
            if isinstance(result, dict):
                # Non-streaming response - convert to streaming format
                return self._create_streaming_response_from_dict(
                    result, request.session_state
                )
            else:
                # Already streaming - wrap it
                return self._create_streaming_response_from_generator(result)

        except Exception as e:
            self.logger.error(f"Chat processing failed for user {user_id}: {str(e)}")
            return self._create_error_streaming_response(str(e), request.session_state)

    def _create_streaming_response_from_dict(
        self, result: dict[str, Any], session_state: str = None
    ) -> StreamingResponse:
        """Convert dict result to streaming response"""

        async def generate():
            # Convert to ChatResponse format
            try:
                message_obj = result.get("message")
                if hasattr(message_obj, "content"):
                    message_content = message_obj.content
                else:
                    message_content = str(message_obj) if message_obj else ""

                # Create response in the format expected by tests
                response_data = {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": message_content,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "session_state": session_state,
                }

                yield f"data: {json.dumps(response_data)}\n\n"
            except Exception as e:
                logger.error(f"Error formatting response: {e}")
                error_data = {
                    "error": f"Error formatting response: {str(e)}",
                    "session_state": session_state,
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache"},
        )

    def _create_streaming_response_from_generator(
        self, result: AsyncGenerator
    ) -> StreamingResponse:
        """Wrap async generator in streaming response"""

        async def generate():
            try:
                async for chunk in result:
                    # Format chunk as NDJSON
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                error_data = {
                    "error": f"Streaming error: {str(e)}",
                    "session_state": None,
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache"},
        )

    def _create_error_streaming_response(
        self, error_message: str, session_state: str = None
    ) -> StreamingResponse:
        """Create error response in streaming format"""

        async def generate():
            error_data = {
                "error": f"The app encountered an error processing your request. Error: {error_message}",
                "session_state": session_state,
            }
            yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache"},
        )


# Global instance
from app.services.session_manager import session_manager

chat_orchestrator = ChatOrchestrator(session_manager=session_manager)
