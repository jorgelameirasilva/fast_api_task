"""
Chat Service - Handles chat business logic with conversation history storage
Single Responsibility: Process chat requests and save conversation history
"""

from typing import Any
from loguru import logger

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.session import SessionMessageCreate
from app.core.setup import get_chat_approach
from .session_service import session_service
import uuid


class ChatService:
    """Service focused on chat operations with conversation history"""

    async def process_chat(
        self,
        request: ChatRequest,
        context: dict[str, Any],
        user_id: str = "default_user",
    ) -> ChatResponse:
        """Process a chat request and save conversation history"""
        logger.info(f"Processing chat with {len(request.messages)} messages")

        try:
            # Handle session management
            session_id = request.session_id or str(uuid.uuid4())
            conversation_history = []

            if request.session_id:
                # Load existing conversation history
                messages = session_service.get_session_messages(
                    request.session_id, user_id
                )
                # Convert to chat format
                conversation_history = [
                    {"role": msg.message["role"], "content": msg.message["content"]}
                    for msg in messages
                ]
                logger.info(
                    f"Loaded {len(conversation_history)} messages from session {request.session_id}"
                )

            # Add current user message to conversation
            user_message = request.messages[-1]
            conversation_history.append(
                {"role": user_message.role, "content": user_message.content}
            )

            # Save user message to database
            user_message_create = SessionMessageCreate(
                user_id=user_id,
                session_id=session_id,
                message={"role": user_message.role, "content": user_message.content},
            )
            session_service.add_message(user_message_create)

            # Process with chat approach
            chat_approach = get_chat_approach()
            if not chat_approach:
                raise ValueError("No chat approach configured")

            approach_result = await chat_approach.run(
                messages=conversation_history,
                stream=request.stream or False,
                context=context,
                session_state=getattr(request, "session_state", None),
            )

            # Extract and save assistant response
            assistant_message = None
            if (
                hasattr(approach_result, "choices")
                and approach_result.choices
                and approach_result.choices[0].message
            ):
                assistant_message = approach_result.choices[0].message
            elif isinstance(approach_result, dict) and "message" in approach_result:
                assistant_message = approach_result["message"]

            if assistant_message:
                assistant_message_create = SessionMessageCreate(
                    user_id=user_id,
                    session_id=session_id,
                    message={
                        "role": assistant_message.role,
                        "content": assistant_message.content,
                    },
                )
                session_service.add_message(assistant_message_create)

            # Add session_id to response
            if hasattr(approach_result, "session_id"):
                approach_result.session_id = session_id
            elif isinstance(approach_result, dict):
                approach_result["session_id"] = session_id

            return approach_result

        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            raise


# Create service instance
chat_service = ChatService()
