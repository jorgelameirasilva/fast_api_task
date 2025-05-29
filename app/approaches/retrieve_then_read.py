"""
Retrieve-Then-Read approach implementation.

This approach follows a simpler pattern where it:
1. Retrieves relevant information based on the query
2. Reads and processes the retrieved information
3. Generates a response based on the retrieved content

This approach is more efficient for simple queries that don't require
complex conversational context.
"""

from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from loguru import logger

from .base import BaseApproach


class RetrieveThenReadApproach(BaseApproach):
    """
    Implementation of the Retrieve-Then-Read approach.

    This approach is ideal for straightforward information retrieval scenarios
    where the query is self-contained and doesn't heavily depend on conversation context.
    """

    def __init__(self):
        super().__init__("RetrieveThenRead")

    async def run(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        session_state: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Execute the Retrieve-Then-Read approach.

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
        # Step 1: Extract the current query
        current_query = await self._extract_query(messages)

        # Step 2: Retrieve relevant information
        retrieved_info = await self._retrieve_information(current_query, context)

        # Step 3: Read and process retrieved information
        processed_content = await self._process_retrieved_content(
            retrieved_info, current_query
        )

        # Step 4: Generate response based on retrieved content
        response_content = await self._generate_response(
            current_query, processed_content, context
        )

        # Step 5: Extract sources
        sources = self._extract_sources(retrieved_info)

        return self.format_response(
            content=response_content,
            sources=sources,
            context={
                "query": current_query,
                "approach_steps": [
                    "extract_query",
                    "retrieve_information",
                    "process_retrieved_content",
                    "generate_response",
                ],
                "retrieval_count": len(retrieved_info),
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
        yield {"status": "extracting_query", "step": 1, "total_steps": 4}

        # Step 1: Extract query
        current_query = await self._extract_query(messages)
        yield {"status": "retrieving_information", "step": 2, "total_steps": 4}

        # Step 2: Retrieve information
        retrieved_info = await self._retrieve_information(current_query, context)
        yield {"status": "processing_content", "step": 3, "total_steps": 4}

        # Step 3: Process content
        processed_content = await self._process_retrieved_content(
            retrieved_info, current_query
        )
        yield {"status": "generating_response", "step": 4, "total_steps": 4}

        # Step 4: Generate response
        response_content = await self._generate_response(
            current_query, processed_content, context
        )

        sources = self._extract_sources(retrieved_info)

        # Yield final response
        yield self.format_response(
            content=response_content,
            sources=sources,
            context={
                "query": current_query,
                "streaming": True,
                "retrieval_count": len(retrieved_info),
                **(context or {}),
            },
        )

    async def _extract_query(self, messages: List[Dict[str, Any]]) -> str:
        """
        Extract the current query from the conversation messages.

        Args:
            messages: List of conversation messages

        Returns:
            The current query string
        """
        logger.debug("Extracting query from messages")

        # Find the latest user message
        for message in reversed(messages):
            if message.get("role") == "user":
                query = message.get("content", "").strip()
                logger.debug(f"Extracted query: {query[:100]}...")
                return query

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

        # Extract context for search
        overrides = context.get("overrides", {}) if context else {}
        auth_claims = context.get("auth_claims") if context else None

        # Build search filter
        search_filter = self.build_filter(overrides, auth_claims)
        logger.debug(f"Using search filter: {search_filter}")

        # Enhanced mock retrieval that considers the query content
        query_lower = query.lower()

        # Simulate different types of documents based on query
        mock_results = []

        if any(
            keyword in query_lower for keyword in ["policy", "procedure", "guidelines"]
        ):
            mock_results.extend(
                [
                    {
                        "id": "policy1",
                        "title": "Company Policy Document",
                        "content": f"This policy document addresses questions related to: {query}. It provides comprehensive guidelines and procedures.",
                        "source": "/documents/policies/policy1.pdf",
                        "relevance_score": 0.95,
                        "category": "policy",
                        "document_type": "policy",
                    },
                    {
                        "id": "procedure1",
                        "title": "Standard Operating Procedure",
                        "content": f"Step-by-step procedure relevant to: {query}. Follow these instructions carefully.",
                        "source": "/documents/procedures/sop1.pdf",
                        "relevance_score": 0.89,
                        "category": "procedure",
                        "document_type": "procedure",
                    },
                ]
            )

        if any(
            keyword in query_lower
            for keyword in ["technical", "how to", "implementation"]
        ):
            mock_results.extend(
                [
                    {
                        "id": "tech1",
                        "title": "Technical Documentation",
                        "content": f"Technical information about: {query}. Includes implementation details and best practices.",
                        "source": "/documents/technical/tech1.pdf",
                        "relevance_score": 0.92,
                        "category": "technical",
                        "document_type": "technical",
                    }
                ]
            )

        # Default general results
        if not mock_results:
            mock_results = [
                {
                    "id": "general1",
                    "title": "General Information Document",
                    "content": f"General information relevant to your query: {query}",
                    "source": "/documents/general/info1.pdf",
                    "relevance_score": 0.75,
                    "category": "general",
                    "document_type": "general",
                },
                {
                    "id": "general2",
                    "title": "Additional Reference Material",
                    "content": f"Additional context and information for: {query}",
                    "source": "/documents/general/ref1.pdf",
                    "relevance_score": 0.70,
                    "category": "general",
                    "document_type": "reference",
                },
            ]

        # Apply category filtering if specified
        selected_category = overrides.get("selected_category")
        if selected_category and selected_category.lower() != "none":
            mock_results = [
                result
                for result in mock_results
                if result.get("category", "").lower() == selected_category.lower()
            ]

        logger.info(f"Retrieved {len(mock_results)} documents")
        return mock_results

    async def _process_retrieved_content(
        self, retrieved_info: List[Dict[str, Any]], query: str
    ) -> Dict[str, Any]:
        """
        Process the retrieved content for response generation.

        Args:
            retrieved_info: List of retrieved information chunks
            query: Original query for context

        Returns:
            Processed content summary
        """
        logger.debug("Processing retrieved content")

        if not retrieved_info:
            return {
                "content_summary": "No relevant information found.",
                "sources_count": 0,
                "average_relevance": 0,
                "content_types": [],
            }

        # Analyze and combine content
        content_pieces = []
        total_relevance = 0
        content_types = set()

        for info in retrieved_info:
            content = info.get("content", "")
            content_pieces.append(content)
            total_relevance += info.get("relevance_score", 0)

            doc_type = info.get("document_type", "unknown")
            content_types.add(doc_type)

        avg_relevance = total_relevance / len(retrieved_info)

        # Create structured content summary
        content_summary = self._create_content_summary(content_pieces, query)

        return {
            "content_summary": content_summary,
            "sources_count": len(retrieved_info),
            "average_relevance": avg_relevance,
            "content_types": list(content_types),
            "raw_content": content_pieces,
        }

    def _create_content_summary(self, content_pieces: List[str], query: str) -> str:
        """
        Create a structured summary of the retrieved content.

        Args:
            content_pieces: List of content strings
            query: Original query

        Returns:
            Structured content summary
        """
        if not content_pieces:
            return "No content available."

        # For simplicity, combine the content with some structure
        combined = " ".join(content_pieces)

        # In a real implementation, this would use NLP to create a proper summary
        if len(combined) > 500:
            summary = combined[:500] + "..."
        else:
            summary = combined

        return summary

    async def _generate_response(
        self,
        query: str,
        processed_content: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """
        Generate the final response based on processed content.

        Args:
            query: Original query
            processed_content: Processed content from retrieval
            context: Additional context

        Returns:
            Generated response string
        """
        logger.debug("Generating response from processed content")

        content_summary = processed_content.get("content_summary", "")
        sources_count = processed_content.get("sources_count", 0)
        avg_relevance = processed_content.get("average_relevance", 0)
        content_types = processed_content.get("content_types", [])

        if sources_count == 0:
            return f"I apologize, but I couldn't find any relevant information for your query: '{query}'. Please try rephrasing your question or contact support for assistance."

        # Build response structure
        response_parts = [
            f"Based on your query: '{query}', I found {sources_count} relevant document(s).",
            "",
        ]

        if content_types:
            types_str = ", ".join(content_types)
            response_parts.append(f"The information comes from {types_str} documents.")
            response_parts.append("")

        response_parts.extend(
            [
                "Here's the relevant information:",
                "",
                content_summary,
                "",
                f"This response is based on {sources_count} source(s) with an average relevance score of {avg_relevance:.2f}.",
                "Generated using the Retrieve-Then-Read approach for efficient information retrieval.",
            ]
        )

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
                    "title": info.get("title", "Unknown Document"),
                    "url": info.get("source", ""),
                    "relevance_score": info.get("relevance_score", 0),
                    "excerpt": (
                        info.get("content", "")[:200] + "..."
                        if len(info.get("content", "")) > 200
                        else info.get("content", "")
                    ),
                    "document_type": info.get("document_type", "unknown"),
                    "category": info.get("category", "general"),
                }
            )

        return sources
