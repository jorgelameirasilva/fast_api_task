"""
Chat Service - Handles chat business logic following SOLID principles
Single Responsibility: Manage chat approach and process chat requests
"""

from typing import Any, Union, Dict
from loguru import logger

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatChoice,
    ChatMessage,
    ChatContentData,
)
from app.schemas.session import SessionMessageCreate
from app.core.setup import get_chat_approach
from .session_service import session_service
import uuid


class ChatService:
    """Service focused solely on chat operations"""

    def __init__(
        self,
    ):
        self.session_storage: dict[str, Any] = {}

    async def process_chat(
        self,
        request: ChatRequest,
        context: dict[str, Any],
        user_id: str = "default_user",
    ) -> ChatResponse:
        """Process a chat request using approaches as primary method - returns ChatResponse"""
        logger.info(f"Processing chat with {len(request.messages)} messages")

        try:
            # Handle session management
            session_id = request.session_id or str(uuid.uuid4())
            conversation_history = []

            if request.session_id:
                # Load existing session messages
                messages = await session_service.get_session_messages(
                    request.session_id, user_id
                )
                # Convert session messages to chat format for approach
                conversation_history = [
                    {"role": msg.message["role"], "content": msg.message["content"]}
                    for msg in messages
                ]
                logger.info(
                    f"Loaded session {request.session_id} with {len(conversation_history)} messages"
                )
            else:
                logger.info(f"Created new session: {session_id}")

            # Add current user message to conversation history
            user_message = request.messages[-1]  # Get the latest user message
            conversation_history.append(
                {"role": user_message.role, "content": user_message.content}
            )

            # Save user message to session
            message_create = SessionMessageCreate(
                user_id=user_id,
                session_id=session_id,
                message={"role": user_message.role, "content": user_message.content},
            )
            await session_service.add_message(message_create)

            # Get chat approach and process
            chat_approach = get_chat_approach()
            if not chat_approach:
                raise ValueError("No chat approach configured")

            session_state = None
            if hasattr(request, "session_state") and request.session_state:
                session_state = request.session_state

            # Use full conversation history for approach
            approach_result = await chat_approach.run(
                messages=conversation_history,
                stream=request.stream or False,
                context=context,
                session_state=session_state,
            )

            # The approach returns a dict with format: {"message": ..., "data_points": ..., "thoughts": ...}
            # We need to convert this to ChatResponse format
            if not isinstance(approach_result, dict):
                raise ValueError("Approach should return a dict")

            # Extract assistant message for session storage
            assistant_message = None
            if "message" in approach_result:
                assistant_message = approach_result["message"]

            if assistant_message:
                # Handle both dict and object formats
                if hasattr(assistant_message, "role") and hasattr(
                    assistant_message, "content"
                ):
                    # It's an object with role and content attributes
                    assistant_message_create = SessionMessageCreate(
                        user_id=user_id,
                        session_id=session_id,
                        message={
                            "role": assistant_message.role,
                            "content": assistant_message.content,
                        },
                    )
                elif isinstance(assistant_message, dict):
                    # It's a dict
                    assistant_message_create = SessionMessageCreate(
                        user_id=user_id,
                        session_id=session_id,
                        message=assistant_message,
                    )
                else:
                    logger.warning(
                        f"Unexpected assistant message format: {type(assistant_message)}"
                    )

                if "assistant_message_create" in locals():
                    await session_service.add_message(assistant_message_create)

            # Convert approach result to ChatResponse format
            # Create ChatMessage from the approach result
            chat_message = ChatMessage(
                role=(
                    assistant_message.role
                    if hasattr(assistant_message, "role")
                    else assistant_message.get("role", "assistant")
                ),
                content=(
                    assistant_message.content
                    if hasattr(assistant_message, "content")
                    else assistant_message.get("content", "")
                ),
            )

            # Create ChatContentData from extra info
            chat_content_data = ChatContentData(
                data_points=approach_result.get("data_points", []),
                thoughts=approach_result.get("thoughts", ""),
            )

            # Create ChatChoice
            chat_choice = ChatChoice(
                message=chat_message,
                content=chat_content_data,
                finish_reason="stop",
            )

            # Create ChatResponse
            chat_response = ChatResponse(
                choices=[chat_choice],
                session_id=session_id,
            )

            return chat_response

        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            raise


# Create service instance
chat_service = ChatService()
