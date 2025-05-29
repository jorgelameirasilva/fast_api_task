"""
Base approach abstract class for implementing different query processing strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from datetime import datetime

from app.schemas.chat import AskRequest, AskResponse


class BaseApproach(ABC):
    """
    Abstract base class for all query processing approaches.

    This class defines the interface that all approach implementations must follow.
    It uses the Strategy Pattern to allow different algorithms for processing queries.
    """

    def __init__(self, name: str):
        """
        Initialize the approach with a name.

        Args:
            name: The name of this approach
        """
        self.name = name

    def build_filter(
        self, overrides: Dict[str, Any], auth_claims: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Build a filter string for search queries.

        Args:
            overrides: Configuration overrides from the request
            auth_claims: Authentication claims for the user

        Returns:
            Filter string or None if no filtering is needed
        """
        filters = []

        # Handle category filtering
        selected_category = overrides.get("selected_category")
        if selected_category and selected_category.lower() != "none":
            # Clean the category name and create filter
            clean_category = selected_category.replace("'", "''")
            filters.append(f"category eq '{clean_category}'")

        # Handle security filtering based on auth claims
        if auth_claims:
            security_filter = self._build_security_filter(overrides, auth_claims)
            if security_filter:
                filters.append(security_filter)

        return " and ".join(filters) if filters else None

    def _build_security_filter(
        self, overrides: Dict[str, Any], auth_claims: Dict[str, Any]
    ) -> Optional[str]:
        """
        Build security-related filters based on authentication claims.

        Args:
            overrides: Configuration overrides
            auth_claims: User authentication claims

        Returns:
            Security filter string or None
        """
        # Placeholder for security filtering logic
        # This would typically check user roles, permissions, etc.
        return None

    @abstractmethod
    async def run(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        session_state: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Execute the approach strategy.

        Args:
            messages: List of conversation messages
            stream: Whether to stream the response
            session_state: Session state for conversation continuity
            context: Additional context for processing

        Returns:
            Response dictionary or async generator for streaming
        """
        pass

    async def run_until_final_call(
        self,
        messages: List[Dict[str, Any]],
        overrides: Dict[str, Any],
        auth_claims: Optional[Dict[str, Any]] = None,
        should_stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the approach until the final call, handling intermediate steps.

        Args:
            messages: Conversation messages
            overrides: Configuration overrides
            auth_claims: Authentication claims
            should_stream: Whether streaming is requested

        Returns:
            Final response dictionary
        """
        # Default implementation - can be overridden by specific approaches
        context = {
            "overrides": overrides,
            "auth_claims": auth_claims,
            "timestamp": datetime.now().isoformat(),
        }

        result = await self.run(
            messages=messages, stream=should_stream, context=context
        )

        if hasattr(result, "__aiter__"):
            # If it's an async generator, collect all results
            final_result = {}
            async for chunk in result:
                final_result.update(chunk)
            return final_result

        return result

    def format_response(
        self,
        content: str,
        sources: List[Dict[str, Any]] = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Format the response in a consistent structure.

        Args:
            content: The response content
            sources: List of source documents
            context: Additional context information

        Returns:
            Formatted response dictionary
        """
        return {
            "content": content,
            "sources": sources or [],
            "context": context or {},
            "approach": self.name,
            "timestamp": datetime.now().isoformat(),
        }

    def __str__(self) -> str:
        """String representation of the approach."""
        return f"{self.__class__.__name__}(name='{self.name}')"

    def __repr__(self) -> str:
        """Detailed string representation of the approach."""
        return self.__str__()
