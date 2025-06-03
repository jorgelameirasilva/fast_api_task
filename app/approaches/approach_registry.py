from typing import Dict, Any, Type, Optional
from loguru import logger

from app.approaches.base import Approach


# Global registry for approaches
_approach_classes: Dict[str, Type[Approach]] = {}
_approach_instances: Dict[str, Approach] = {}


def register_approach(name: str, approach_class: Type[Approach]) -> None:
    """Register an approach class with a name"""
    logger.debug(f"Registered approach: {name} -> {approach_class.__name__}")
    _approach_classes[name] = approach_class


def register_approach_instance(name: str, approach_instance: Approach) -> None:
    """Register a pre-configured approach instance"""
    logger.debug(f"Registered pre-configured approach instance: {name}")
    _approach_instances[name] = approach_instance


def get_approach_class(name: str) -> Optional[Type[Approach]]:
    """Get an approach class by name"""
    return _approach_classes.get(name)


def get_approach_instance(name: str) -> Optional[Approach]:
    """Get a pre-configured approach instance by name"""
    return _approach_instances.get(name)


def get_best_approach(approach_name: Optional[str] = None) -> Approach:
    """
    Get the best approach instance based on the name provided.
    Defaults to retrieve_then_read if no name provided or not found.
    """
    if approach_name:
        # Try to get pre-configured instance first
        instance = get_approach_instance(approach_name)
        if instance:
            return instance

        # Try to get class and instantiate (placeholder)
        approach_class = get_approach_class(approach_name)
        if approach_class:
            logger.warning(
                f"Creating new instance of {approach_name} - consider pre-configuring"
            )
            return approach_class()

    # Default fallback
    default_instance = get_approach_instance("retrieve_then_read")
    if default_instance:
        return default_instance

    # Ultimate fallback - import and create default
    logger.warning("Using fallback approach creation")
    from app.approaches.retrieve_then_read import RetrieveThenReadApproach

    return RetrieveThenReadApproach()


def list_approaches() -> Dict[str, str]:
    """List all registered approaches"""
    result = {}

    for name, cls in _approach_classes.items():
        result[name] = cls.__name__

    for name, instance in _approach_instances.items():
        result[name] = f"{instance.__class__.__name__} (instance)"

    return result


# Auto-register approach classes when module is imported
def _auto_register_approaches():
    """Auto-register known approach classes"""
    try:
        from app.approaches.retrieve_then_read import RetrieveThenReadApproach
        from app.approaches.chat_read_retrieve_read import ChatReadRetrieveReadApproach

        register_approach("retrieve_then_read", RetrieveThenReadApproach)
        register_approach("chat_read_retrieve_read", ChatReadRetrieveReadApproach)
        register_approach("retrievethenread", RetrieveThenReadApproach)
        register_approach("chatreadretrieveread", ChatReadRetrieveReadApproach)
        register_approach("default", RetrieveThenReadApproach)

    except ImportError as e:
        logger.error(f"Failed to auto-register approaches: {e}")


# Initialize auto-registration
_auto_register_approaches()
