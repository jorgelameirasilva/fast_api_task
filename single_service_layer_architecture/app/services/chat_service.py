"""
Chat Service - Single service combining coordination + business logic
"""

import uuid
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger

from app.auth.dependencies import AuthUser
from app.repositories.llm_repository import LLMRepository, LLMMessage, LLMResponse
from app.repositories.search_repository import (
    SearchRepository,
    SearchResult,
    SearchQuery,
)
from app.repositories.cosmos_repository import (
    CosmosRepository,
    CosmosMessage,
    CosmosSession,
)


@dataclass
class ChatMessage:
    """Chat message model"""

    id: str
    content: str
    role: str  # "user" or "assistant"
    timestamp: datetime
    user_id: str
    session_id: str
    metadata: Optional[Dict] = None


@dataclass
class ChatSession:
    """Chat session model"""

    session_id: str
    user_id: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime
    context: Optional[Dict] = None


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


class ChatService:
    """
    Single service handling both coordination and business logic for chat
    Combines what used to be Application Service + Domain Service
    """

    def __init__(self):
        # Initialize repositories
        self.llm_repository = LLMRepository()
        self.search_repository = SearchRepository()
        self.cosmos_repository = CosmosRepository()

        # Business logic configuration
        self.max_messages_in_context = 10
        self.max_context_length = 4000
        self.confidence_threshold = 0.7
        self.max_session_duration_hours = 24
        self.max_sessions_per_user = 50

        # In-memory storage fallback (when Cosmos DB not available)
        self.sessions: Dict[str, ChatSession] = {}
        self.cosmos_connected = False

    async def initialize(self):
        """Initialize the service and connect to Cosmos DB"""
        self.cosmos_connected = await self.cosmos_repository.connect()
        if self.cosmos_connected:
            logger.info("ChatService initialized with Cosmos DB")
        else:
            logger.warning(
                "ChatService initialized with in-memory storage (Cosmos DB unavailable)"
            )

    async def _load_session_messages(
        self, session_id: str, user_id: str
    ) -> List[ChatMessage]:
        """Load recent messages for a session from Cosmos DB"""

        if not self.cosmos_connected:
            return []

        cosmos_messages = await self.cosmos_repository.get_session_messages(
            session_id=session_id,
            user_id=user_id,
            limit=self.max_messages_in_context * 2,
        )

        # Convert to ChatMessage objects
        messages = []
        for msg in cosmos_messages:
            messages.append(
                ChatMessage(
                    id=msg.id,
                    content=msg.content,
                    role=msg.role,
                    timestamp=datetime.fromisoformat(msg.timestamp),
                    user_id=msg.user_id,
                    session_id=msg.session_id,
                    metadata=msg.metadata,
                )
            )

        return messages

    # =============================================================================
    # PUBLIC API METHODS (called by endpoints)
    # =============================================================================

    async def send_message(self, request: ChatRequest, user: AuthUser) -> ChatResponse:
        """Send a chat message and get response"""

        try:
            logger.info(f"Processing chat message for user {user.user_id}")

            # Validate message (business logic)
            self._validate_message(request.message)

            # Get or create session (coordination)
            session = await self._get_or_create_session(
                request.session_id, user.user_id
            )

            # Determine if we should use search context (business logic)
            should_search = request.use_search and self._should_use_search_context(
                request.message, session
            )

            # Get context if needed (coordination)
            context_summary = None
            context_sources = []
            if should_search:
                context_summary, context_sources = await self._get_search_context(
                    session, request.message
                )

            # Prepare messages for LLM (business logic)
            llm_messages = self._prepare_llm_messages(
                session, request.message, context_summary
            )

            # Generate response (coordination)
            llm_response = await self.llm_repository.generate_response(
                llm_messages, temperature=request.temperature
            )

            # Create and store messages (business logic + coordination)
            user_message_id = str(uuid.uuid4())
            assistant_message_id = str(uuid.uuid4())

            user_message = self._create_message(
                content=request.message,
                role="user",
                user_id=user.user_id,
                session_id=session.session_id,
                message_id=user_message_id,
            )

            assistant_message = self._create_message(
                content=llm_response.content,
                role="assistant",
                user_id=user.user_id,
                session_id=session.session_id,
                message_id=assistant_message_id,
            )

            # Update session (business logic)
            await self._update_session_with_messages(
                session, user_message, assistant_message
            )

            return ChatResponse(
                message=llm_response.content,
                session_id=session.session_id,
                message_id=assistant_message_id,
                timestamp=assistant_message.timestamp,
                context_used=bool(context_summary),
                context_sources=context_sources,
            )

        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            raise

    async def send_message_stream(
        self, request: ChatRequest, user: AuthUser
    ) -> AsyncGenerator[Dict, None]:
        """Send chat with streaming response"""

        try:
            logger.info(f"Processing streaming chat for user {user.user_id}")

            # Validate message (business logic)
            self._validate_message(request.message)

            # Get or create session (coordination)
            session = await self._get_or_create_session(
                request.session_id, user.user_id
            )

            # Send session info
            yield {
                "type": "session",
                "session_id": session.session_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Determine if we should use search context (business logic)
            should_search = request.use_search and self._should_use_search_context(
                request.message, session
            )

            # Get context if needed (coordination)
            context_summary = None
            context_sources = []
            if should_search:
                yield {"type": "status", "content": "Searching for relevant context..."}
                context_summary, context_sources = await self._get_search_context(
                    session, request.message
                )

                if context_sources:
                    yield {"type": "context", "sources": context_sources}

            # Prepare messages for LLM (business logic)
            llm_messages = self._prepare_llm_messages(
                session, request.message, context_summary
            )

            yield {"type": "status", "content": "Generating response..."}

            # Stream response (coordination)
            full_response = ""
            assistant_message_id = str(uuid.uuid4())

            async for chunk in self.llm_repository.generate_streaming_response(
                llm_messages, temperature=request.temperature
            ):
                full_response += chunk
                yield {"type": "content", "content": chunk}

            # Create and store messages (business logic + coordination)
            user_message_id = str(uuid.uuid4())

            user_message = self._create_message(
                content=request.message,
                role="user",
                user_id=user.user_id,
                session_id=session.session_id,
                message_id=user_message_id,
            )

            assistant_message = self._create_message(
                content=full_response,
                role="assistant",
                user_id=user.user_id,
                session_id=session.session_id,
                message_id=assistant_message_id,
            )

            # Update session (business logic)
            await self._update_session_with_messages(
                session, user_message, assistant_message
            )

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

        if self.cosmos_connected:
            # Get session from Cosmos DB
            cosmos_session = await self.cosmos_repository.get_session(
                session_id, user.user_id
            )
            if not cosmos_session:
                raise ValueError("Session not found")

            # Load messages from Cosmos DB
            messages = await self._load_session_messages(session_id, user.user_id)

            # Create session object for summary
            session = ChatSession(
                session_id=cosmos_session.id,
                user_id=cosmos_session.user_id,
                messages=messages,
                created_at=datetime.fromisoformat(cosmos_session.created_at),
                updated_at=datetime.fromisoformat(cosmos_session.updated_at),
                context=cosmos_session.context,
            )
        else:
            # Fallback to in-memory storage
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError("Session not found")

            # Check access (business logic)
            if session.user_id != user.user_id:
                raise PermissionError("User can only access their own sessions")

        # Get session summary (business logic)
        summary = self._get_session_summary(session)

        # Format messages (coordination)
        formatted_messages = []
        for msg in session.messages:
            formatted_messages.append(
                {
                    "id": msg.id,
                    "content": msg.content,
                    "role": msg.role,
                    "timestamp": msg.timestamp.isoformat(),
                }
            )

        return {"session": summary, "messages": formatted_messages}

    async def get_user_sessions(self, user: AuthUser) -> List[Dict]:
        """Get all sessions for a user"""

        user_sessions = [
            session
            for session in self.sessions.values()
            if session.user_id == user.user_id
        ]

        # Sort by last activity (business logic)
        user_sessions.sort(key=lambda s: s.updated_at, reverse=True)

        # Return session summaries (coordination)
        return [self._get_session_summary(session) for session in user_sessions]

    async def delete_session(self, session_id: str, user: AuthUser) -> bool:
        """Delete a chat session"""

        session = self.sessions.get(session_id)
        if not session:
            return False

        # Check access (business logic)
        if session.user_id != user.user_id:
            raise PermissionError("User can only delete their own sessions")

        # Delete session (coordination)
        del self.sessions[session_id]
        logger.info(f"Deleted session {session_id} for user {user.user_id}")
        return True

    # =============================================================================
    # PRIVATE METHODS (internal business logic + coordination)
    # =============================================================================

    def _validate_message(self, content: str) -> None:
        """Validate chat message content (business logic)"""

        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")

        if len(content) > 10000:
            raise ValueError("Message too long (max 10,000 characters)")

        # Check for potentially harmful content (basic check)
        harmful_patterns = ["<script", "javascript:", "eval(", "exec("]
        if any(pattern in content.lower() for pattern in harmful_patterns):
            raise ValueError("Message contains potentially harmful content")

    def _should_use_search_context(
        self, user_message: str, session: ChatSession
    ) -> bool:
        """Determine if search context should be used (business logic)"""

        # Keywords that suggest factual questions
        factual_keywords = [
            "what",
            "how",
            "when",
            "where",
            "why",
            "who",
            "which",
            "explain",
            "describe",
            "define",
            "tell me about",
            "what is",
            "how to",
            "documentation",
            "guide",
            "tutorial",
        ]

        message_lower = user_message.lower()

        # Check if message contains factual question keywords
        has_factual_keywords = any(
            keyword in message_lower for keyword in factual_keywords
        )

        # Check if it's not a greeting or casual conversation
        casual_patterns = [
            "hello",
            "hi",
            "hey",
            "thanks",
            "thank you",
            "bye",
            "goodbye",
            "how are you",
            "good morning",
            "good afternoon",
            "good evening",
        ]

        is_casual = any(pattern in message_lower for pattern in casual_patterns)

        # Use search if it seems factual and not casual
        return has_factual_keywords and not is_casual

    async def _get_search_context(
        self, session: ChatSession, user_message: str
    ) -> tuple[Optional[str], List[str]]:
        """Get search context for the conversation (coordination)"""

        try:
            # Create search query (business logic)
            search_query = self._create_search_query_from_conversation(
                session, user_message
            )

            # Perform search (coordination)
            search_results = await self.search_repository.semantic_search(search_query)

            # Process search results (business logic)
            context_summary, sources = self._process_search_results(search_results)

            logger.info(f"Retrieved {len(sources)} relevant documents")

            return context_summary, sources

        except Exception as e:
            logger.error(f"Error getting search context: {e}")
            return None, []

    def _create_search_query_from_conversation(
        self, session: ChatSession, new_message: str
    ) -> SearchQuery:
        """Create search query based on conversation context (business logic)"""

        # Get recent messages for context
        recent_messages = self._get_recent_messages(session.messages, limit=5)

        # Build query from recent conversation
        conversation_context = []
        for msg in recent_messages[-3:]:  # Last 3 messages for context
            if msg.role == "user":
                conversation_context.append(msg.content)

        # Combine current message with recent context
        query_parts = conversation_context + [new_message]
        query_text = " ".join(query_parts)

        return SearchQuery(
            text=query_text, limit=5, threshold=self.confidence_threshold
        )

    def _process_search_results(
        self, search_results: List[SearchResult]
    ) -> tuple[Optional[str], List[str]]:
        """Process search results into context (business logic)"""

        if not search_results:
            return None, []

        # Filter results by confidence threshold
        relevant_results = [
            result
            for result in search_results
            if result.score >= self.confidence_threshold
        ]

        if not relevant_results:
            # Keep top 2 even if low confidence
            relevant_results = search_results[:2]

        # Build context summary
        context_parts = []
        total_length = 0
        sources = []

        for i, result in enumerate(relevant_results):
            if total_length >= self.max_context_length:
                break

            # Truncate content if needed
            content = result.content
            if total_length + len(content) > self.max_context_length:
                remaining_space = self.max_context_length - total_length
                content = content[:remaining_space] + "..."

            context_part = f"Source {i+1} (Score: {result.score:.2f}):\n{content}"
            context_parts.append(context_part)
            total_length += len(context_part)

            if result.source:
                sources.append(result.source)

        context_summary = "\n\n".join(context_parts) if context_parts else None
        return context_summary, sources

    def _prepare_llm_messages(
        self,
        session: ChatSession,
        new_user_message: str,
        context_summary: Optional[str] = None,
    ) -> List[LLMMessage]:
        """Prepare messages for LLM (business logic)"""

        # System message with context
        system_content = self._build_system_message(context_summary)
        messages = [LLMMessage(role="system", content=system_content)]

        # Add recent conversation history
        recent_messages = self._get_recent_messages(session.messages)
        for msg in recent_messages:
            messages.append(LLMMessage(role=msg.role, content=msg.content))

        # Add new user message
        messages.append(LLMMessage(role="user", content=new_user_message))

        return messages

    def _build_system_message(self, context_summary: Optional[str]) -> str:
        """Build system message with context (business logic)"""

        base_prompt = """You are a helpful AI assistant. Provide accurate and helpful responses based on the conversation history."""

        if not context_summary:
            return base_prompt

        context_prompt = f"""
{base_prompt}

You have access to the following relevant information:

{context_summary}

Use this information to provide accurate and contextual responses. If the provided context doesn't contain relevant information for the user's question, clearly state that and provide a general helpful response.
"""

        return context_prompt.strip()

    def _get_recent_messages(
        self, messages: List[ChatMessage], limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get recent messages from conversation history (business logic)"""

        limit = limit or self.max_messages_in_context

        # Sort by timestamp and get most recent
        sorted_messages = sorted(messages, key=lambda m: m.timestamp)
        return sorted_messages[-limit:]

    def _create_message(
        self, content: str, role: str, user_id: str, session_id: str, message_id: str
    ) -> ChatMessage:
        """Create a new chat message (business logic)"""

        return ChatMessage(
            id=message_id,
            content=content,
            role=role,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
        )

    async def _update_session_with_messages(
        self,
        session: ChatSession,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> None:
        """Update session with new messages (business logic)"""

        # Save messages to database
        if self.cosmos_connected:
            # Save messages to Cosmos DB
            await self.cosmos_repository.save_message(
                message_id=user_message.id,
                content=user_message.content,
                role=user_message.role,
                user_id=user_message.user_id,
                session_id=user_message.session_id,
                timestamp=user_message.timestamp,
                metadata=user_message.metadata,
            )

            await self.cosmos_repository.save_message(
                message_id=assistant_message.id,
                content=assistant_message.content,
                role=assistant_message.role,
                user_id=assistant_message.user_id,
                session_id=assistant_message.session_id,
                timestamp=assistant_message.timestamp,
                metadata=assistant_message.metadata,
            )

            # Update session metadata
            session_title = self._generate_session_title(
                session.messages + [user_message, assistant_message]
            )
            await self.cosmos_repository.update_session(
                session_id=session.session_id,
                user_id=session.user_id,
                title=session_title,
                message_count=len(session.messages) + 2,
            )
        else:
            # Fallback to in-memory storage
            session.messages.extend([user_message, assistant_message])
            session.updated_at = datetime.utcnow()

            # Trim old messages if session gets too long
            if len(session.messages) > self.max_messages_in_context * 2:
                # Keep recent messages
                session.messages = session.messages[
                    -(self.max_messages_in_context * 2) :
                ]

            # Store updated session
            self.sessions[session.session_id] = session

    async def _get_or_create_session(
        self, session_id: Optional[str], user_id: str
    ) -> ChatSession:
        """Get existing session or create new one (coordination + business logic)"""

        if self.cosmos_connected:
            # Use Cosmos DB
            if session_id:
                # Try to get existing session
                cosmos_session = await self.cosmos_repository.get_session(
                    session_id, user_id
                )
                if cosmos_session:
                    # Convert to ChatSession and load recent messages
                    messages = await self._load_session_messages(session_id, user_id)
                    session = ChatSession(
                        session_id=cosmos_session.id,
                        user_id=cosmos_session.user_id,
                        messages=messages,
                        created_at=datetime.fromisoformat(cosmos_session.created_at),
                        updated_at=datetime.fromisoformat(cosmos_session.updated_at),
                        context=cosmos_session.context,
                    )

                    # Validate session (business logic)
                    if self._is_session_valid(session):
                        return session
                    else:
                        logger.warning(
                            f"Invalid session {session_id}, creating new one"
                        )

            # Create new session
            new_session = self._create_new_session(user_id, session_id)

            # Save to Cosmos DB
            await self.cosmos_repository.create_session(
                session_id=new_session.session_id,
                user_id=new_session.user_id,
                context=new_session.context,
                title=None,
            )

            logger.info(
                f"Created new session {new_session.session_id} for user {user_id}"
            )
            return new_session
        else:
            # Fallback to in-memory storage
            if session_id and session_id in self.sessions:
                session = self.sessions[session_id]

                # Validate session (business logic)
                if not self._is_session_valid(session):
                    logger.warning(f"Invalid session {session_id}, creating new one")
                    # Create new session
                    new_session = self._create_new_session(user_id)
                    self.sessions[new_session.session_id] = new_session
                    return new_session

                return session
            else:
                # Create new session
                new_session = self._create_new_session(user_id, session_id)
                self.sessions[new_session.session_id] = new_session
                logger.info(
                    f"Created new session {new_session.session_id} for user {user_id}"
                )
                return new_session

    def _create_new_session(
        self, user_id: str, session_id: Optional[str] = None
    ) -> ChatSession:
        """Create a new chat session (business logic)"""

        if not session_id:
            session_id = str(uuid.uuid4())

        now = datetime.utcnow()

        return ChatSession(
            session_id=session_id,
            user_id=user_id,
            messages=[],
            created_at=now,
            updated_at=now,
            context={},
        )

    def _is_session_valid(self, session: ChatSession) -> bool:
        """Check if a session is valid and active (business logic)"""

        if not session:
            return False

        # Check if session is too old
        session_age = datetime.utcnow() - session.created_at
        if session_age.total_seconds() > (self.max_session_duration_hours * 3600):
            return False

        return True

    def _get_session_summary(self, session: ChatSession) -> Dict:
        """Get a summary of the session (business logic)"""

        if not session.messages:
            return {
                "session_id": session.session_id,
                "status": "empty",
                "created_at": session.created_at.isoformat(),
                "message_count": 0,
                "duration": "0 minutes",
            }

        # Calculate session statistics
        user_messages = [msg for msg in session.messages if msg.role == "user"]
        assistant_messages = [
            msg for msg in session.messages if msg.role == "assistant"
        ]

        duration = session.updated_at - session.created_at
        duration_minutes = int(duration.total_seconds() / 60)

        return {
            "session_id": session.session_id,
            "title": self._generate_session_title(session.messages),
            "status": "active",
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": len(session.messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "duration": f"{duration_minutes} minutes",
        }

    def _generate_session_title(self, messages: List[ChatMessage]) -> str:
        """Generate an appropriate title for the session (business logic)"""

        if not messages:
            return "New Chat Session"

        # Find the first user message
        first_user_message = next((msg for msg in messages if msg.role == "user"), None)

        if not first_user_message:
            return "New Chat Session"

        # Use first 50 characters of the first user message
        title = first_user_message.content[:50].strip()

        # Clean up the title
        title = title.replace("\n", " ").replace("\r", " ")
        while "  " in title:  # Remove multiple spaces
            title = title.replace("  ", " ")

        # Add ellipsis if truncated
        if len(first_user_message.content) > 50:
            title += "..."

        return title or "New Chat Session"
