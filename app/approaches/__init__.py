"""
Approaches package for different query processing strategies.

This module implements the Strategy Pattern for handling different types of
query processing approaches in the chat application.
"""

from .base import BaseApproach
from .chat_read_retrieve_read import ChatReadRetrieveReadApproach
from .retrieve_then_read import RetrieveThenReadApproach
from .approach_registry import (
    ApproachRegistry,
    get_approach,
    get_best_approach,
    list_available_approaches,
    register_approach,
)

__all__ = [
    "BaseApproach",
    "ChatReadRetrieveReadApproach",
    "RetrieveThenReadApproach",
    "ApproachRegistry",
    "get_approach",
    "get_best_approach",
    "list_available_approaches",
    "register_approach",
]
