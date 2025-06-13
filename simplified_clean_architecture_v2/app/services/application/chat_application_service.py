"""
Chat Application Service - Coordinates chat workflow
"""

import uuid
from typing import Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from app.auth.dependencies import AuthUser
from app.repositories.llm_repository import LLMRepository, LLMMessage
from app.repositories.search_repository import SearchRepository, SearchQuery
from app.services.domain.chat_domain_service import (
    ChatDomainService,
    ChatSession,
    ChatMessage,
    ChatContext,
)
from app.services.domain.session_domain_service import SessionDomainService


@dataclass
class ChatRequest:
    """Chat request DTO"""

    message: str
    session_id: Optional[str] = None
    use_search: bool = True
    temperature: float = 0.7


@dataclass
class ChatResponse:
    """Chat response DTO"""

    message: str
    session_id: str
    message_id: str
    timestamp: datetime
    context_used: bool = False
    context_sources: List[str] = None

    def __post_init__(self):
        if self.context_sources is None:
            self.context_sources = []


class ChatApplicationService:
    """Application service that coordinates chat workflow"""

    def __init__(self):
        # Initialize repositories
        self.llm_repository = LLMRepository()
        self.search_repository = SearchRepository()

        # Initialize domain services
        self.chat_domain = ChatDomainService()
        self.session_domain = SessionDomainService()

        # In-memory storage (replace with actual database in production)
        self.sessions: Dict[str, ChatSession] = {}

    async def process_chat_message(
        self, request: ChatRequest, user: AuthUser
    ) -> ChatResponse:
        """Process a chat message and return response"""

        try:
            logger.info(f"Processing chat message for user {user.user_id}")

            # Validate message
            is_valid, error_msg = self.chat_domain.validate_chat_message(
                request.message
            )
            if not is_valid:
                raise ValueError(error_msg)

            # Get or create session
            session = await self._get_or_create_session(
                request.session_id, user.user_id
            )

            # Determine if we should use search context
            should_search = (
                request.use_search
                and self.chat_domain.should_use_search_context(request.message, session)
            )

            # Get context if needed
            context = None
            if should_search:
                context = await self._get_search_context(session, request.message)

            # Prepare messages for LLM
            llm_messages = self.chat_domain.prepare_chat_messages(
                session, request.message, context
            )

            # Generate response
            llm_response = await self.llm_repository.generate_response(
                llm_messages, temperature=request.temperature
            )

            # Create message objects
            user_message_id = str(uuid.uuid4())
            assistant_message_id = str(uuid.uuid4())

            user_message = self.chat_domain.create_chat_message(
                content=request.message,
                role="user",
                user_id=user.user_id,
                session_id=session.session_id,
                message_id=user_message_id,
            )

            assistant_message = self.chat_domain.create_chat_message(
                content=llm_response.content,
                role="assistant",
                user_id=user.user_id,
                session_id=session.session_id,
                message_id=assistant_message_id,
            )

            # Update session
            updated_session = self.chat_domain.update_session_with_messages(
                session, user_message, assistant_message
            )
            self.sessions[session.session_id] = updated_session

            # Prepare response
            context_sources = []
            if context and context.relevant_documents:
                context_sources = [
                    doc.source for doc in context.relevant_documents if doc.source
                ]

            return ChatResponse(
                message=llm_response.content,
                session_id=session.session_id,
                message_id=assistant_message_id,
                timestamp=assistant_message.timestamp,
                context_used=bool(context),
                context_sources=context_sources,
            )

        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            raise

    async def process_streaming_chat(
        self, request: ChatRequest, user: AuthUser
    ) -> AsyncGenerator[Dict, None]:
        """Process chat with streaming response"""

        try:
            logger.info(f"Processing streaming chat for user {user.user_id}")

            # Validate message
            is_valid, error_msg = self.chat_domain.validate_chat_message(
                request.message
            )
            if not is_valid:
                yield {"type": "error", "content": error_msg}
                return

            # Get or create session
            session = await self._get_or_create_session(
                request.session_id, user.user_id
            )

            # Send session info
            yield {
                "type": "session",
                "session_id": session.session_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Determine if we should use search context
            should_search = (
                request.use_search
                and self.chat_domain.should_use_search_context(request.message, session)
            )

            # Get context if needed
            context = None
            if should_search:
                yield {"type": "status", "content": "Searching for relevant context..."}
                context = await self._get_search_context(session, request.message)

                if context and context.relevant_documents:
                    yield {
                        "type": "context",
                        "sources": [
                            doc.source
                            for doc in context.relevant_documents
                            if doc.source
                        ],
                    }

            # Prepare messages for LLM
            llm_messages = self.chat_domain.prepare_chat_messages(
                session, request.message, context
            )

            yield {"type": "status", "content": "Generating response..."}

            # Stream response
            full_response = ""
            assistant_message_id = str(uuid.uuid4())

            async for chunk in self.llm_repository.generate_streaming_response(
                llm_messages, temperature=request.temperature
            ):
                full_response += chunk
                yield {"type": "content", "content": chunk}

            # Create message objects and update session
            user_message_id = str(uuid.uuid4())

            user_message = self.chat_domain.create_chat_message(
                content=request.message,
                role="user",
                user_id=user.user_id,
                session_id=session.session_id,
                message_id=user_message_id,
            )

            assistant_message = self.chat_domain.create_chat_message(
                content=full_response,
                role="assistant",
                user_id=user.user_id,
                session_id=session.session_id,
                message_id=assistant_message_id,
            )

            # Update session
            updated_session = self.chat_domain.update_session_with_messages(
                session, user_message, assistant_message
            )
            self.sessions[session.session_id] = updated_session

            # Send completion
            yield {
                "type": "complete",
                "message_id": assistant_message_id,
                "timestamp": assistant_message.timestamp.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in streaming chat: {e}")
            yield {"type": "error", "content": f"An error occurred: {str(e)}"}

    async def get_session_history(self, session_id: str, user: AuthUser) -> Dict:
        """Get chat session history"""

        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")

        # Check access
        can_access, error_msg = self.session_domain.can_user_access_session(
            user.user_id, session
        )
        if not can_access:
            raise PermissionError(error_msg)

        # Get session summary
        summary = self.session_domain.get_session_summary(session)

        # Format messages
        messages = []
        for msg in session.messages:
            messages.append(
                {
                    "id": msg.id,
                    "content": msg.content,
                    "role": msg.role,
                    "timestamp": msg.timestamp.isoformat(),
                }
            )

        return {"session": summary, "messages": messages}

    async def get_user_sessions(self, user: AuthUser) -> List[Dict]:
        """Get all sessions for a user"""

        user_sessions = [
            session
            for session in self.sessions.values()
            if session.user_id == user.user_id
        ]

        # Sort by last activity
        user_sessions.sort(key=lambda s: s.updated_at, reverse=True)

        # Return session summaries
        return [
            self.session_domain.get_session_summary(session)
            for session in user_sessions
        ]

    async def delete_session(self, session_id: str, user: AuthUser) -> bool:
        """Delete a chat session"""

        session = self.sessions.get(session_id)
        if not session:
            return False

        # Check access
        can_access, error_msg = self.session_domain.can_user_access_session(
            user.user_id, session
        )
        if not can_access:
            raise PermissionError(error_msg)

        # Delete session
        del self.sessions[session_id]
        logger.info(f"Deleted session {session_id} for user {user.user_id}")
        return True

    async def _get_or_create_session(
        self, session_id: Optional[str], user_id: str
    ) -> ChatSession:
        """Get existing session or create new one"""

        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]

            # Validate session
            is_valid, error_msg = self.session_domain.is_session_valid(session)
            if not is_valid:
                logger.warning(f"Invalid session {session_id}: {error_msg}")
                # Create new session
                new_session = self.session_domain.create_new_session(user_id)
                self.sessions[new_session.session_id] = new_session
                return new_session

            return session
        else:
            # Create new session
            new_session = self.session_domain.create_new_session(user_id, session_id)
            self.sessions[new_session.session_id] = new_session
            logger.info(
                f"Created new session {new_session.session_id} for user {user_id}"
            )
            return new_session

    async def _get_search_context(
        self, session: ChatSession, user_message: str
    ) -> Optional[ChatContext]:
        """Get search context for the conversation"""

        try:
            # Create search query
            search_query = self.chat_domain.create_search_query_from_conversation(
                session, user_message
            )

            # Perform search
            search_results = await self.search_repository.semantic_search(search_query)

            # Process search results into context
            context = self.chat_domain.process_search_context(search_results)

            logger.info(
                f"Retrieved {len(context.relevant_documents)} relevant documents "
                f"with confidence {context.confidence_score:.2f}"
            )

            return context

        except Exception as e:
            logger.error(f"Error getting search context: {e}")
            return None
