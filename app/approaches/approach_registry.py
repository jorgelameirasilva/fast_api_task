"""
Approach Registry for managing different query processing approaches.

This module provides a registry system for managing approach implementations
using the Factory pattern with both class-based and instance-based registration.
"""

from typing import Dict, Type, Optional, Union
from loguru import logger

from .base import BaseApproach
from .retrieve_then_read import RetrieveThenReadApproach
from .chat_read_retrieve_read import ChatReadRetrieveReadApproach


class ApproachRegistry:
    """
    Registry for managing approach implementations.
    Supports both class-based registration (legacy) and instance-based registration.
    """

    def __init__(self):
        """Initialize the registry with empty collections."""
        self._approaches: Dict[str, Type[BaseApproach]] = {}
        self._instances: Dict[str, BaseApproach] = {}
        self._preconfigured_instances: Dict[str, BaseApproach] = {}

        # Register built-in approaches (class-based for backward compatibility)
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
        Register a new approach implementation by class.

        Args:
            name: Name to register the approach under
            approach_class: The approach class to register
        """
        name = name.lower().strip()
        self._approaches[name] = approach_class
        logger.debug(f"Registered approach: {name} -> {approach_class.__name__}")

    def register_instance(self, name: str, approach_instance: BaseApproach):
        """
        Register a pre-configured approach instance.
        This is used by the setup system to provide dependency-injected instances.

        Args:
            name: Name to register the approach under
            approach_instance: Pre-configured approach instance
        """
        name = name.lower().strip()
        self._preconfigured_instances[name] = approach_instance

        # Also register aliases for the same instance
        if "retrieve" in name and "read" in name:
            if "chat" in name:
                # Register ChatReadRetrieveRead aliases
                aliases = ["chatreadretrieveread", "chat_read_retrieve_read"]
            else:
                # Register RetrieveThenRead aliases
                aliases = ["retrievethenread", "retrieve_then_read", "default"]

            for alias in aliases:
                if alias.lower() != name:
                    self._preconfigured_instances[alias.lower()] = approach_instance

        logger.debug(f"Registered pre-configured approach instance: {name}")

    def get_approach(self, name: str) -> BaseApproach:
        """
        Get an approach instance by name.
        Prioritizes pre-configured instances from setup over class-based instances.

        Args:
            name: Name of the approach to retrieve

        Returns:
            Approach instance

        Raises:
            ValueError: If the approach is not found
        """
        name = name.lower().strip()

        # First check for pre-configured instances (from setup)
        if name in self._preconfigured_instances:
            return self._preconfigured_instances[name]

        # Then check for existing class-based instances
        if name in self._instances:
            return self._instances[name]

        # Create new instance if class is registered (fallback for backward compatibility)
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
        # Try pre-configured default first
        if "default" in self._preconfigured_instances:
            return self._preconfigured_instances["default"]

        # Fallback to class-based default
        return self.get_approach("retrieve_then_read")

    def has_preconfigured_instances(self) -> bool:
        """
        Check if any pre-configured instances are available.

        Returns:
            True if pre-configured instances are available, False otherwise
        """
        return len(self._preconfigured_instances) > 0

    def list_approaches(self) -> Dict[str, str]:
        """
        List all registered approaches (both class-based and pre-configured).

        Returns:
            Dictionary mapping approach names to class names
        """
        result = {}

        # Add pre-configured instances
        for name, instance in self._preconfigured_instances.items():
            result[name] = instance.__class__.__name__

        # Add class-based approaches (if not already covered by pre-configured)
        for name, approach_class in self._approaches.items():
            if name not in result:
                result[name] = approach_class.__name__

        return result

    def is_registered(self, name: str) -> bool:
        """
        Check if an approach is registered (either pre-configured or class-based).

        Args:
            name: Name of the approach to check

        Returns:
            True if the approach is registered, False otherwise
        """
        name = name.lower().strip()
        return (
            name in self._preconfigured_instances
            or name in self._approaches
            or name in self._instances
        )

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
    Register a new approach class in the global registry.

    Args:
        name: Name to register the approach under
        approach_class: The approach class to register
    """
    _approach_registry.register(name, approach_class)


def register_approach_instance(name: str, approach_instance: BaseApproach):
    """
    Register a pre-configured approach instance in the global registry.
    This is used by the setup system.

    Args:
        name: Name to register the approach under
        approach_instance: Pre-configured approach instance
    """
    _approach_registry.register_instance(name, approach_instance)
