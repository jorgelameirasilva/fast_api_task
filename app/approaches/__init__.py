from app.approaches.base import Approach
from app.approaches.retrieve_then_read import RetrieveThenReadApproach
from app.approaches.chat_read_retrieve_read import ChatReadRetrieveReadApproach
from app.approaches.approach_registry import (
    register_approach,
    register_approach_instance,
    get_approach_class,
    get_approach_instance,
    get_best_approach,
    list_approaches,
)

__all__ = [
    "Approach",
    "RetrieveThenReadApproach",
    "ChatReadRetrieveReadApproach",
    "register_approach",
    "register_approach_instance",
    "get_approach_class",
    "get_approach_instance",
    "get_best_approach",
    "list_approaches",
]
