"""
Response Generation Service
Handles LLM-based response generation with context management
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.repositories.llm_repository import (
    LLMRepository,
    LLMRequest,
    LLMMessage,
    LLMResponse,
)
from app.repositories.search_repository import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class GeneratedResponse:
    """Generated response with metadata"""

    content: str
    confidence: float
    sources_used: List[str]
    processing_time_ms: int
    model_info: Dict[str, Any]


class ResponseGenerationService:
    """Domain service for LLM-based response generation"""

    def __init__(self, llm_repository: LLMRepository):
        self.llm_repository = llm_repository
        self.system_prompt = self._get_system_prompt()
        logger.info("Initialized ResponseGenerationService")

    async def generate_response(
        self,
        query: str,
        search_results: List[SearchResult],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedResponse:
        """
        Generate response using LLM with search results as context
        """
        logger.info(f"Generating response for query: {query[:50]}...")

        try:
            # Step 1: Build context from search results
            context_text = self._build_context_from_results(search_results)

            # Step 2: Construct messages for LLM
            messages = self._build_messages(query, context_text, conversation_history)

            # Step 3: Generate response
            llm_request = LLMRequest(
                messages=messages, temperature=0.7, max_tokens=1000
            )

            llm_response = await self.llm_repository.generate_response(llm_request)

            # Step 4: Post-process response
            processed_response = await self._post_process_response(
                llm_response, search_results, query
            )

            return processed_response

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            raise

    async def generate_chat_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        search_results: List[SearchResult],
        conversation_id: str,
    ) -> GeneratedResponse:
        """
        Generate chat response with conversation context
        """
        logger.info(f"Generating chat response for conversation: {conversation_id}")

        try:
            # Build conversation context
            context_text = self._build_context_from_results(search_results)

            # Construct messages with full conversation history
            messages = [
                LLMMessage(role="system", content=self._get_chat_system_prompt())
            ]

            # Add conversation history
            for hist_msg in conversation_history[-10:]:  # Limit to last 10 messages
                messages.append(
                    LLMMessage(role=hist_msg["role"], content=hist_msg["content"])
                )

            # Add context and current message
            if context_text:
                messages.append(
                    LLMMessage(
                        role="system", content=f"Relevant context:\n{context_text}"
                    )
                )

            messages.append(LLMMessage(role="user", content=message))

            # Generate response
            llm_request = LLMRequest(
                messages=messages,
                temperature=0.8,  # Slightly higher for conversational tone
                max_tokens=800,
            )

            llm_response = await self.llm_repository.generate_response(llm_request)

            return await self._post_process_response(
                llm_response, search_results, message
            )

        except Exception as e:
            logger.error(f"Chat response generation failed: {e}")
            raise

    def _build_context_from_results(self, results: List[SearchResult]) -> str:
        """
        Build context string from search results
        """
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results[:5], 1):  # Limit to top 5 results
            context_parts.append(
                f"Source {i} (Score: {result.score:.2f}):\n{result.content}\n"
            )

        return "\n".join(context_parts)

    def _build_messages(
        self, query: str, context: str, history: Optional[List[Dict[str, str]]] = None
    ) -> List[LLMMessage]:
        """
        Build message list for LLM request
        """
        messages = [LLMMessage(role="system", content=self.system_prompt)]

        # Add conversation history if provided
        if history:
            for msg in history[-5:]:  # Limit to last 5 messages
                messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        # Add context if available
        if context:
            messages.append(
                LLMMessage(
                    role="system",
                    content=f"Use the following information to help answer the question:\n\n{context}",
                )
            )

        # Add user query
        messages.append(LLMMessage(role="user", content=query))

        return messages

    async def _post_process_response(
        self,
        llm_response: LLMResponse,
        search_results: List[SearchResult],
        original_query: str,
    ) -> GeneratedResponse:
        """
        Post-process LLM response and add metadata
        """
        # Calculate confidence based on various factors
        confidence = self._calculate_confidence(llm_response, search_results)

        # Extract sources used
        sources_used = [result.source for result in search_results]

        return GeneratedResponse(
            content=llm_response.content,
            confidence=confidence,
            sources_used=sources_used,
            processing_time_ms=llm_response.processing_time_ms,
            model_info={
                "model": llm_response.model,
                "finish_reason": llm_response.finish_reason,
                "tokens_used": llm_response.usage.get("total_tokens", 0),
            },
        )

    def _calculate_confidence(
        self, llm_response: LLMResponse, search_results: List[SearchResult]
    ) -> float:
        """
        Calculate confidence score for the response
        """
        base_confidence = 0.7

        # Adjust based on search result quality
        if search_results:
            avg_score = sum(r.score for r in search_results) / len(search_results)
            base_confidence += (avg_score - 0.5) * 0.3

        # Adjust based on response completion
        if llm_response.finish_reason == "stop":
            base_confidence += 0.1

        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, base_confidence))

    def _get_system_prompt(self) -> str:
        """Get system prompt for general responses"""
        return """You are a helpful AI assistant that provides accurate and informative responses.
        
        Guidelines:
        - Use the provided context to answer questions accurately
        - If information is not available in the context, state this clearly
        - Provide concise but comprehensive answers
        - Cite sources when appropriate
        - Be helpful and professional
        """

    def _get_chat_system_prompt(self) -> str:
        """Get system prompt for chat responses"""
        return """You are a helpful AI assistant in a conversational chat interface.
        
        Guidelines:
        - Maintain context from the conversation history
        - Provide natural, conversational responses
        - Use the provided search context when relevant
        - Ask clarifying questions when needed
        - Be friendly and engaging while remaining professional
        """

    async def health_check(self) -> Dict[str, str]:
        """Check service health"""
        try:
            llm_health = await self.llm_repository.health_check()
            return {
                "service": "ResponseGenerationService",
                "status": "healthy",
                "llm_repository": llm_health.get("status", "unknown"),
            }
        except Exception as e:
            return {
                "service": "ResponseGenerationService",
                "status": "unhealthy",
                "error": str(e),
            }
