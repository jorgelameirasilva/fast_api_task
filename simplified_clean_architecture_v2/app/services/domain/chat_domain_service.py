"""
Chat Domain Service - Pure business logic for chat functionality
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from app.repositories.llm_repository import LLMMessage, LLMResponse
from app.repositories.search_repository import SearchResult, SearchQuery


@dataclass
class ChatMessage:
    """Chat message domain model"""

    id: str
    content: str
    role: str  # "user" or "assistant"
    timestamp: datetime
    user_id: str
    session_id: str
    metadata: Optional[Dict] = None


@dataclass
class ChatSession:
    """Chat session domain model"""

    session_id: str
    user_id: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime
    context: Optional[Dict] = None


@dataclass
class ChatContext:
    """Chat context from search results"""

    relevant_documents: List[SearchResult]
    context_summary: str
    confidence_score: float


class ChatDomainService:
    """Pure business logic for chat operations"""

    def __init__(self):
        self.max_messages_in_context = 10
        self.max_context_length = 4000
        self.confidence_threshold = 0.7

    def prepare_chat_messages(
        self,
        session: ChatSession,
        new_user_message: str,
        context: Optional[ChatContext] = None,
    ) -> List[LLMMessage]:
        """Prepare messages for LLM based on chat history and context"""

        # System message with context
        system_content = self._build_system_message(context)
        messages = [LLMMessage(role="system", content=system_content)]

        # Add recent conversation history
        recent_messages = self._get_recent_messages(session.messages)
        for msg in recent_messages:
            messages.append(LLMMessage(role=msg.role, content=msg.content))

        # Add new user message
        messages.append(LLMMessage(role="user", content=new_user_message))

        return messages

    def process_search_context(self, search_results: List[SearchResult]) -> ChatContext:
        """Process search results into chat context"""

        if not search_results:
            return ChatContext(
                relevant_documents=[],
                context_summary="No relevant context found.",
                confidence_score=0.0,
            )

        # Filter results by confidence threshold
        relevant_results = [
            result
            for result in search_results
            if result.score >= self.confidence_threshold
        ]

        if not relevant_results:
            return ChatContext(
                relevant_documents=search_results[
                    :2
                ],  # Keep top 2 even if low confidence
                context_summary="Limited relevant context available.",
                confidence_score=0.3,
            )

        # Build context summary
        context_summary = self._build_context_summary(relevant_results)

        # Calculate overall confidence
        avg_confidence = sum(r.score for r in relevant_results) / len(relevant_results)

        return ChatContext(
            relevant_documents=relevant_results,
            context_summary=context_summary,
            confidence_score=avg_confidence,
        )

    def create_search_query_from_conversation(
        self, session: ChatSession, new_message: str
    ) -> SearchQuery:
        """Create search query based on conversation context"""

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

    def validate_chat_message(self, content: str) -> tuple[bool, Optional[str]]:
        """Validate chat message content"""

        if not content or not content.strip():
            return False, "Message content cannot be empty"

        if len(content) > 10000:
            return False, "Message too long (max 10,000 characters)"

        # Check for potentially harmful content (basic check)
        harmful_patterns = ["<script", "javascript:", "eval(", "exec("]
        if any(pattern in content.lower() for pattern in harmful_patterns):
            return False, "Message contains potentially harmful content"

        return True, None

    def should_use_search_context(
        self, user_message: str, session: ChatSession
    ) -> bool:
        """Determine if search context should be used for this message"""

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

    def _build_system_message(self, context: Optional[ChatContext]) -> str:
        """Build system message with context"""

        base_prompt = """You are a helpful AI assistant. Provide accurate and helpful responses based on the conversation history."""

        if not context or not context.relevant_documents:
            return base_prompt

        context_prompt = f"""
{base_prompt}

You have access to the following relevant information:

{context.context_summary}

Use this information to provide accurate and contextual responses. If the provided context doesn't contain relevant information for the user's question, clearly state that and provide a general helpful response.
"""

        return context_prompt.strip()

    def _build_context_summary(self, results: List[SearchResult]) -> str:
        """Build context summary from search results"""

        context_parts = []
        total_length = 0

        for i, result in enumerate(results):
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

        return "\n\n".join(context_parts)

    def _get_recent_messages(
        self, messages: List[ChatMessage], limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get recent messages from conversation history"""

        limit = limit or self.max_messages_in_context

        # Sort by timestamp and get most recent
        sorted_messages = sorted(messages, key=lambda m: m.timestamp)
        return sorted_messages[-limit:]

    def create_chat_message(
        self, content: str, role: str, user_id: str, session_id: str, message_id: str
    ) -> ChatMessage:
        """Create a new chat message"""

        return ChatMessage(
            id=message_id,
            content=content,
            role=role,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
        )

    def update_session_with_messages(
        self,
        session: ChatSession,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> ChatSession:
        """Update session with new messages"""

        # Add messages to session
        session.messages.extend([user_message, assistant_message])
        session.updated_at = datetime.utcnow()

        # Trim old messages if session gets too long
        if len(session.messages) > self.max_messages_in_context * 2:
            # Keep recent messages
            session.messages = session.messages[-(self.max_messages_in_context * 2) :]

        return session
