"""
Response Generation Service - Domain Service Layer.
Handles LLM-based response generation with context and prompt management.
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from app.repositories.llm_repository import LLMRepository, LLMMessage, LLMRequest
from app.repositories.search_repository import SearchResult


class ResponseGenerationService:
    """
    Service responsible for generating responses using LLM with retrieved context.
    Handles prompt engineering, context management, and response formatting.
    """

    def __init__(self, llm_repository: LLMRepository):
        self.llm_repository = llm_repository

        # System prompts for different response types
        self.system_prompts = {
            "ask": self._get_ask_system_prompt(),
            "chat": self._get_chat_system_prompt(),
        }

    async def generate_contextual_response(
        self,
        user_query: str,
        search_results: List[SearchResult],
        response_type: str = "ask",
        stream: bool = False,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate a contextual response using retrieved documents.

        Args:
            user_query: The user's question
            search_results: Retrieved documents for context
            response_type: Type of response ("ask" or "chat")
            stream: Whether to stream the response
            conversation_history: Previous conversation messages

        Returns:
            Generated response content
        """
        logger.info(
            f"Generating {response_type} response for query: {user_query[:50]}..."
        )

        try:
            # Build the prompt with context
            messages = self._build_context_messages(
                user_query=user_query,
                search_results=search_results,
                response_type=response_type,
                conversation_history=conversation_history,
            )

            # Create LLM request
            request = LLMRequest(
                messages=messages, temperature=0.7, max_tokens=1000, stream=stream
            )

            # Generate response
            if stream:
                # Handle streaming response
                response_content = ""
                async for chunk in self.llm_repository.generate_stream(request):
                    response_content += chunk
                return response_content
            else:
                response = await self.llm_repository.generate_response(request)
                return response.content

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._get_fallback_response(user_query, response_type)

    def _build_context_messages(
        self,
        user_query: str,
        search_results: List[SearchResult],
        response_type: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[LLMMessage]:
        """
        Build the message list for LLM request with proper context.
        """
        messages = []

        # Add system prompt
        system_prompt = self.system_prompts.get(
            response_type, self.system_prompts["ask"]
        )
        messages.append(LLMMessage(role="system", content=system_prompt))

        # Add conversation history for chat
        if conversation_history and response_type == "chat":
            for msg in conversation_history[-5:]:  # Keep last 5 messages
                messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        # Build context from search results
        context_content = self._build_context_content(search_results)

        # Create the main user message with context
        user_message_content = self._format_user_message(
            user_query=user_query,
            context_content=context_content,
            response_type=response_type,
        )

        messages.append(LLMMessage(role="user", content=user_message_content))

        return messages

    def _build_context_content(self, search_results: List[SearchResult]) -> str:
        """
        Build formatted context content from search results.
        """
        if not search_results:
            return "No relevant documents found."

        context_parts = []
        for i, result in enumerate(search_results[:5], 1):  # Limit to top 5
            context_part = f"""
Source {i}: {result.title} ({result.source})
Content: {result.content[:500]}{'...' if len(result.content) > 500 else ''}
Relevance: {result.relevance_score:.2f}
"""
            context_parts.append(context_part)

        return "\n".join(context_parts)

    def _format_user_message(
        self, user_query: str, context_content: str, response_type: str
    ) -> str:
        """
        Format the user message with context for the LLM.
        """
        if response_type == "ask":
            return f"""
Based on the following context from employee documentation, please answer the user's question.

CONTEXT:
{context_content}

USER QUESTION: {user_query}

Please provide a helpful, accurate answer based on the context above. If the context doesn't contain enough information to answer the question, please say so clearly.
"""
        else:  # chat
            return f"""
Continue this conversation using the following context from employee documentation.

CONTEXT:
{context_content}

USER: {user_query}

Please respond naturally while incorporating relevant information from the context when appropriate.
"""

    def _get_ask_system_prompt(self) -> str:
        """Get system prompt for ask-type responses."""
        return """You are a helpful AI assistant for employees of a company. Your role is to answer questions about employee benefits, policies, and procedures based on the company's documentation.

Guidelines:
- Provide accurate, helpful answers based on the provided context
- Be concise but thorough in your explanations
- If the context doesn't contain enough information, clearly state that
- Always maintain a professional and friendly tone
- Include relevant details like deadlines, requirements, or exceptions when mentioned in the context
- For policy questions, cite the relevant source when possible"""

    def _get_chat_system_prompt(self) -> str:
        """Get system prompt for chat-type responses."""
        return """You are a conversational AI assistant helping employees with questions about company policies, benefits, and procedures. You maintain context across the conversation and provide helpful, accurate information.

Guidelines:
- Engage in natural conversation while staying focused on work-related topics
- Remember and reference previous parts of the conversation when relevant
- Provide accurate information based on company documentation
- Ask clarifying questions if the user's request is unclear
- Maintain a helpful, professional, and friendly tone
- If you don't have enough information, suggest how the employee might find the answer"""

    def _get_fallback_response(self, user_query: str, response_type: str) -> str:
        """
        Generate a fallback response when LLM generation fails.
        """
        if response_type == "chat":
            return (
                "I apologize, but I'm having trouble generating a response right now. "
                f"Regarding your question about '{user_query}', I'd recommend checking the "
                "employee handbook or contacting HR for assistance."
            )
        else:  # ask
            return (
                "I apologize, but I'm unable to process your request at the moment. "
                "Please try rephrasing your question or contact support for help with "
                f"'{user_query}'."
            )
