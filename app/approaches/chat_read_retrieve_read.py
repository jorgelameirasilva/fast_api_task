"""
Chat-Read-Retrieve-Read approach implementation.

This approach follows a pattern where it:
1. Processes the chat context
2. Reads and understands the query
3. Retrieves relevant information
4. Reads the retrieved information
5. Generates a comprehensive response
"""

from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from loguru import logger

from .base import BaseApproach


class ChatReadRetrieveReadApproach(BaseApproach):
    """
    Implementation of the Chat-Read-Retrieve-Read approach.

    This approach is ideal for conversational scenarios where context from
    previous messages is important and needs to be combined with retrieved information.
    """

    def __init__(self):
        super().__init__("ChatReadRetrieveRead")

    async def run(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        session_state: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Execute the Chat-Read-Retrieve-Read approach.

        Args:
            messages: List of conversation messages
            stream: Whether to stream the response
            session_state: Session state for conversation continuity
            context: Additional context for processing

        Returns:
            Response dictionary or async generator for streaming
        """
        logger.info(f"Running {self.name} approach with {len(messages)} messages")

        if stream:
            return self._run_streaming(messages, session_state, context)
        else:
            return await self._run_non_streaming(messages, session_state, context)

    async def _run_non_streaming(
        self,
        messages: List[Dict[str, Any]],
        session_state: Optional[Any],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute the approach without streaming.

        Args:
            messages: Conversation messages
            session_state: Session state
            context: Additional context

        Returns:
            Complete response dictionary
        """
        # Step 1: Process chat context
        chat_context = await self._process_chat_context(messages, session_state)

        # Step 2: Extract and understand the current query
        current_query = await self._extract_current_query(messages, chat_context)

        # Step 3: Retrieve relevant information
        retrieved_info = await self._retrieve_information(current_query, context)

        # Step 4: Read and process retrieved information
        processed_info = await self._process_retrieved_information(
            retrieved_info, current_query
        )

        # Step 5: Generate comprehensive response
        response_content = await self._generate_response(
            current_query, chat_context, processed_info, context
        )

        # Step 6: Extract sources from retrieved information
        sources = self._extract_sources(retrieved_info)

        return self.format_response(
            content=response_content,
            sources=sources,
            context={
                "chat_context": chat_context,
                "query": current_query,
                "approach_steps": [
                    "process_chat_context",
                    "extract_current_query",
                    "retrieve_information",
                    "process_retrieved_information",
                    "generate_response",
                ],
                **(context or {}),
            },
        )

    async def _run_streaming(
        self,
        messages: List[Dict[str, Any]],
        session_state: Optional[Any],
        context: Optional[Dict[str, Any]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute the approach with streaming.

        Args:
            messages: Conversation messages
            session_state: Session state
            context: Additional context

        Yields:
            Streaming response chunks
        """
        # Yield initial status
        yield {"status": "processing_context", "step": 1, "total_steps": 5}

        # Step 1: Process chat context
        chat_context = await self._process_chat_context(messages, session_state)
        yield {"status": "extracting_query", "step": 2, "total_steps": 5}

        # Step 2: Extract current query
        current_query = await self._extract_current_query(messages, chat_context)
        yield {"status": "retrieving_information", "step": 3, "total_steps": 5}

        # Step 3: Retrieve information
        retrieved_info = await self._retrieve_information(current_query, context)
        yield {"status": "processing_information", "step": 4, "total_steps": 5}

        # Step 4: Process retrieved information
        processed_info = await self._process_retrieved_information(
            retrieved_info, current_query
        )
        yield {"status": "generating_response", "step": 5, "total_steps": 5}

        # Step 5: Generate response (can be streamed in chunks)
        response_content = await self._generate_response(
            current_query, chat_context, processed_info, context
        )

        sources = self._extract_sources(retrieved_info)

        # Yield final response
        yield self.format_response(
            content=response_content,
            sources=sources,
            context={
                "chat_context": chat_context,
                "query": current_query,
                "streaming": True,
                **(context or {}),
            },
        )

    async def _process_chat_context(
        self, messages: List[Dict[str, Any]], session_state: Optional[Any]
    ) -> Dict[str, Any]:
        """
        Process the chat context from previous messages.

        Args:
            messages: List of conversation messages
            session_state: Session state

        Returns:
            Processed chat context
        """
        logger.debug("Processing chat context from messages")

        # Extract conversation history
        conversation_summary = []
        user_intent = None

        for message in messages[-5:]:  # Consider last 5 messages for context
            role = message.get("role", "")
            content = message.get("content", "")

            if role == "user":
                conversation_summary.append(f"User: {content}")
                user_intent = content  # Latest user intent
            elif role == "assistant":
                conversation_summary.append(f"Assistant: {content}")

        return {
            "conversation_summary": "\n".join(conversation_summary),
            "user_intent": user_intent,
            "message_count": len(messages),
            "session_state": session_state,
        }

    async def _extract_current_query(
        self, messages: List[Dict[str, Any]], chat_context: Dict[str, Any]
    ) -> str:
        """
        Extract and understand the current query from the conversation.

        Args:
            messages: Conversation messages
            chat_context: Processed chat context

        Returns:
            Current query string
        """
        logger.debug("Extracting current query from conversation")

        # Get the latest user message
        for message in reversed(messages):
            if message.get("role") == "user":
                current_query = message.get("content", "")
                logger.debug(f"Extracted query: {current_query[:100]}...")
                return current_query

        return "No query found"

    async def _retrieve_information(
        self, query: str, context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant information for the query.

        Args:
            query: The search query
            context: Additional context including filters

        Returns:
            List of retrieved information chunks
        """
        logger.debug(f"Retrieving information for query: {query[:50]}...")

        # Extract search filters from context
        overrides = context.get("overrides", {}) if context else {}
        auth_claims = context.get("auth_claims") if context else None

        # Build search filter
        search_filter = self.build_filter(overrides, auth_claims)
        logger.debug(f"Search filter: {search_filter}")

        # Placeholder for actual search implementation
        # This would typically call Azure Search, Elasticsearch, etc.
        mock_results = [
            {
                "id": "doc1",
                "title": "Relevant Document 1",
                "content": f"This document contains information relevant to: {query}",
                "source": "/documents/doc1.pdf",
                "relevance_score": 0.95,
                "category": "general",
            },
            {
                "id": "doc2",
                "title": "Relevant Document 2",
                "content": f"Additional context for query: {query}",
                "source": "/documents/doc2.pdf",
                "relevance_score": 0.87,
                "category": "specific",
            },
        ]

        logger.info(f"Retrieved {len(mock_results)} documents")
        return mock_results

    async def _process_retrieved_information(
        self, retrieved_info: List[Dict[str, Any]], query: str
    ) -> Dict[str, Any]:
        """
        Process and analyze the retrieved information.

        Args:
            retrieved_info: List of retrieved information chunks
            query: Original query for context

        Returns:
            Processed information summary
        """
        logger.debug("Processing retrieved information")

        # Combine and analyze retrieved content
        combined_content = []
        total_relevance = 0
        sources_count = len(retrieved_info)

        for info in retrieved_info:
            combined_content.append(info.get("content", ""))
            total_relevance += info.get("relevance_score", 0)

        avg_relevance = total_relevance / max(sources_count, 1)

        return {
            "combined_content": " ".join(combined_content),
            "sources_count": sources_count,
            "average_relevance": avg_relevance,
            "query_context": query,
        }

    async def _generate_response(
        self,
        query: str,
        chat_context: Dict[str, Any],
        processed_info: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """
        Generate the final response based on all processed information.

        Args:
            query: Original query
            chat_context: Processed chat context
            processed_info: Processed retrieved information
            context: Additional context

        Returns:
            Generated response string
        """
        logger.debug("Generating comprehensive response")

        # This would typically call an LLM with all the context
        # For now, return a structured placeholder response

        response_parts = [
            f"Based on your question: '{query}'",
            f"And considering our conversation context with {chat_context.get('message_count', 0)} messages,",
            f"I found {processed_info.get('sources_count', 0)} relevant sources",
            f"with an average relevance score of {processed_info.get('average_relevance', 0):.2f}.",
            "",
            "Here's my comprehensive response:",
            processed_info.get("combined_content", "No specific content found."),
            "",
            "This response was generated using the Chat-Read-Retrieve-Read approach,",
            "which ensures both conversational context and retrieved information are considered.",
        ]

        return "\n".join(response_parts)

    def _extract_sources(
        self, retrieved_info: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract source information for citations.

        Args:
            retrieved_info: Retrieved information chunks

        Returns:
            List of source dictionaries
        """
        sources = []
        for info in retrieved_info:
            sources.append(
                {
                    "title": info.get("title", "Unknown"),
                    "url": info.get("source", ""),
                    "relevance_score": info.get("relevance_score", 0),
                    "excerpt": info.get("content", "")[:200] + "...",
                }
            )

        return sources
