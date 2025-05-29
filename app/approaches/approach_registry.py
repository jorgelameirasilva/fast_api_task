"""
Approach registry for managing and selecting different query processing approaches.
"""

from typing import Dict, Type, Optional
from loguru import logger

from .base import BaseApproach
from .chat_read_retrieve_read import ChatReadRetrieveReadApproach
from .retrieve_then_read import RetrieveThenReadApproach


class ApproachRegistry:
    """
    Registry for managing different approach implementations.

    This class follows the Factory Pattern to create and manage approach instances.
    """

    def __init__(self):
        """Initialize the registry with available approaches."""
        self._approaches: Dict[str, Type[BaseApproach]] = {}
        self._instances: Dict[str, BaseApproach] = {}

        # Register built-in approaches
        self._register_builtin_approaches()

    def _register_builtin_approaches(self):
        """Register all built-in approach implementations."""
        self.register("chat_read_retrieve_read", ChatReadRetrieveReadApproach)
        self.register("retrieve_then_read", RetrieveThenReadApproach)

        # Add aliases for easier access
        self.register("chatreadretrieveread", ChatReadRetrieveReadApproach)
        self.register("retrievethenread", RetrieveThenReadApproach)
        self.register("default", RetrieveThenReadApproach)  # Default approach

    def register(self, name: str, approach_class: Type[BaseApproach]):
        """
        Register a new approach implementation.

        Args:
            name: Name to register the approach under
            approach_class: The approach class to register
        """
        name = name.lower().strip()
        self._approaches[name] = approach_class
        logger.debug(f"Registered approach: {name} -> {approach_class.__name__}")

    def get_approach(self, name: str) -> BaseApproach:
        """
        Get an approach instance by name.

        Args:
            name: Name of the approach to retrieve

        Returns:
            Approach instance

        Raises:
            ValueError: If the approach is not found
        """
        name = name.lower().strip()

        # Return existing instance if available
        if name in self._instances:
            return self._instances[name]

        # Create new instance if class is registered
        if name in self._approaches:
            approach_class = self._approaches[name]
            instance = approach_class()
            self._instances[name] = instance
            logger.debug(f"Created new approach instance: {name}")
            return instance

        # Fallback to default if name not found
        logger.warning(f"Approach '{name}' not found, falling back to default")
        return self.get_default_approach()

    def get_default_approach(self) -> BaseApproach:
        """
        Get the default approach instance.

        Returns:
            Default approach instance
        """
        return self.get_approach("default")

    def list_approaches(self) -> Dict[str, str]:
        """
        List all registered approaches.

        Returns:
            Dictionary mapping approach names to class names
        """
        return {
            name: approach_class.__name__
            for name, approach_class in self._approaches.items()
        }

    def is_registered(self, name: str) -> bool:
        """
        Check if an approach is registered.

        Args:
            name: Name of the approach to check

        Returns:
            True if the approach is registered, False otherwise
        """
        return name.lower().strip() in self._approaches

    def determine_best_approach(
        self, query: str, context: Optional[Dict] = None, message_count: int = 1
    ) -> str:
        """
        Determine the best approach for a given query and context.

        Args:
            query: The user query
            context: Additional context information
            message_count: Number of messages in the conversation

        Returns:
            Name of the recommended approach
        """
        logger.debug(f"Determining best approach for query: {query[:50]}...")

        query_lower = query.lower()

        # Use ChatReadRetrieveRead for conversational contexts
        if message_count > 2:
            logger.debug("Using ChatReadRetrieveRead for multi-turn conversation")
            return "chat_read_retrieve_read"

        # Use ChatReadRetrieveRead for complex queries that benefit from context
        complex_indicators = [
            "follow up",
            "previous",
            "earlier",
            "we discussed",
            "you mentioned",
            "continue",
            "also",
            "additionally",
            "furthermore",
            "elaborate",
            "explain more",
            "tell me more",
            "details about",
        ]

        if any(indicator in query_lower for indicator in complex_indicators):
            logger.debug("Using ChatReadRetrieveRead for complex/contextual query")
            return "chat_read_retrieve_read"

        # Use RetrieveThenRead for simple, standalone queries
        logger.debug("Using RetrieveThenRead for simple query")
        return "retrieve_then_read"


# Global registry instance
_approach_registry = ApproachRegistry()


def get_approach(name: Optional[str] = None) -> BaseApproach:
    """
    Get an approach instance from the global registry.

    Args:
        name: Name of the approach to retrieve. If None, returns default.

    Returns:
        Approach instance
    """
    if name is None:
        return _approach_registry.get_default_approach()
    return _approach_registry.get_approach(name)


def get_best_approach(
    query: str, context: Optional[Dict] = None, message_count: int = 1
) -> BaseApproach:
    """
    Get the best approach for a given query and context.

    Args:
        query: The user query
        context: Additional context information
        message_count: Number of messages in the conversation

    Returns:
        Best approach instance for the given parameters
    """
    approach_name = _approach_registry.determine_best_approach(
        query=query, context=context, message_count=message_count
    )
    return _approach_registry.get_approach(approach_name)


def list_available_approaches() -> Dict[str, str]:
    """
    List all available approaches.

    Returns:
        Dictionary mapping approach names to class names
    """
    return _approach_registry.list_approaches()


def register_approach(name: str, approach_class: Type[BaseApproach]):
    """
    Register a new approach in the global registry.

    Args:
        name: Name to register the approach under
        approach_class: The approach class to register
    """
    _approach_registry.register(name, approach_class)
