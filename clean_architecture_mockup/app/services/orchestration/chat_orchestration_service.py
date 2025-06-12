"""
Chat Orchestration Service
Coordinates the complete chat workflow with conversation context management
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.domain.query_processing_service import QueryProcessingService
from app.services.domain.response_generation_service import ResponseGenerationService

logger = logging.getLogger(__name__)


class ChatOrchestrationService:
    """Application service that orchestrates the complete chat workflow"""

    def __init__(
        self,
        query_processing_service: QueryProcessingService,
        response_generation_service: ResponseGenerationService,
    ):
        self.query_processing_service = query_processing_service
        self.response_generation_service = response_generation_service
        # In-memory conversation storage (replace with persistent storage in production)
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("Initialized ChatOrchestrationService")

    async def process_chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        max_results: int = 3,  # Fewer results for chat context
    ) -> Dict[str, Any]:
        """
        Complete chat workflow orchestration

        Steps:
        1. Manage conversation context
        2. Process message with conversation context
        3. Execute search if needed
        4. Generate contextual response
        5. Update conversation history
        """
        start_time = datetime.now()

        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        logger.info(f"Processing chat message for conversation: {conversation_id}")

        try:
            # Step 1: Get or initialize conversation history
            conversation_history = self._get_conversation_history(
                conversation_id, history
            )

            # Step 2: Process message with context awareness
            processed_query = await self.query_processing_service.process_query(
                query=message,
                context=self._build_conversation_context(conversation_history),
                max_results=max_results,
            )

            logger.info(
                f"Found {len(processed_query.search_results)} search results for chat"
            )

            # Step 3: Generate chat response with full conversation context
            generated_response = (
                await self.response_generation_service.generate_chat_response(
                    message=message,
                    conversation_history=conversation_history,
                    search_results=processed_query.search_results,
                    conversation_id=conversation_id,
                )
            )

            # Step 4: Update conversation history
            self._update_conversation_history(
                conversation_id, message, generated_response.content
            )

            # Step 5: Calculate processing time
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Step 6: Build chat response
            response = {
                "response": generated_response.content,
                "conversation_id": conversation_id,
                "sources": self._format_chat_sources(processed_query.search_results),
                "processing_time_ms": processing_time,
                "metadata": {
                    "conversation_length": len(
                        self.conversations.get(conversation_id, [])
                    ),
                    "search_enhanced": len(processed_query.search_results) > 0,
                    "model_info": generated_response.model_info,
                },
            }

            logger.info(f"Chat response generated in {processing_time}ms")
            return response

        except Exception as e:
            logger.error(f"Chat orchestration failed: {e}")
            # Return error response
            return {
                "response": "I apologize, but I encountered an error. Please try rephrasing your question.",
                "conversation_id": conversation_id,
                "sources": [],
                "processing_time_ms": int(
                    (datetime.now() - start_time).total_seconds() * 1000
                ),
                "error": str(e),
            }

    def _get_conversation_history(
        self,
        conversation_id: str,
        provided_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """Get conversation history from storage or provided data"""
        if provided_history:
            # Use provided history and store it
            self.conversations[conversation_id] = provided_history
            return provided_history

        # Return stored conversation or empty list
        return self.conversations.get(conversation_id, [])

    def _build_conversation_context(
        self, history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Build context from conversation history for query processing"""
        if not history:
            return {}

        # Extract themes and topics from recent messages
        recent_messages = history[-5:]  # Last 5 messages
        topics = []

        for msg in recent_messages:
            if msg.get("role") == "user":
                # Simple keyword extraction (in production, use more sophisticated NLP)
                words = msg.get("content", "").lower().split()
                topics.extend([w for w in words if len(w) > 4])

        return {
            "conversation_context": True,
            "recent_topics": list(set(topics))[:10],  # Limit to 10 unique topics
            "conversation_length": len(history),
        }

    def _update_conversation_history(
        self, conversation_id: str, user_message: str, assistant_response: str
    ):
        """Update conversation history with new messages"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        # Add user message
        self.conversations[conversation_id].append(
            {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Add assistant response
        self.conversations[conversation_id].append(
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Limit conversation history (keep last 50 messages)
        if len(self.conversations[conversation_id]) > 50:
            self.conversations[conversation_id] = self.conversations[conversation_id][
                -50:
            ]

    def _format_chat_sources(self, search_results) -> List[Dict[str, Any]]:
        """Format search results for chat response (more concise than ask)"""
        formatted_sources = []

        # Only include top 3 sources for chat to keep response clean
        for i, result in enumerate(search_results[:3], 1):
            formatted_sources.append(
                {
                    "id": i,
                    "title": result.metadata.get("title", f"Source {i}"),
                    "score": result.score,
                    "source": result.source,
                }
            )

        return formatted_sources

    async def get_conversation_history(
        self, conversation_id: str
    ) -> List[Dict[str, str]]:
        """Get full conversation history for a given conversation ID"""
        return self.conversations.get(conversation_id, [])

    async def clear_conversation(self, conversation_id: str) -> bool:
        """Clear conversation history for a given conversation ID"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"Cleared conversation: {conversation_id}")
            return True
        return False

    async def health_check(self) -> Dict[str, str]:
        """Check orchestration service health"""
        try:
            # Check all dependent services
            query_health = await self.query_processing_service.health_check()
            response_health = await self.response_generation_service.health_check()

            # Determine overall health
            overall_status = "healthy"
            if (
                query_health.get("status") != "healthy"
                or response_health.get("status") != "healthy"
            ):
                overall_status = "degraded"

            return {
                "service": "ChatOrchestrationService",
                "status": overall_status,
                "active_conversations": len(self.conversations),
                "dependencies": {
                    "query_processing": query_health.get("status", "unknown"),
                    "response_generation": response_health.get("status", "unknown"),
                },
            }

        except Exception as e:
            return {
                "service": "ChatOrchestrationService",
                "status": "unhealthy",
                "error": str(e),
            }
