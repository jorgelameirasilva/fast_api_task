"""
API endpoints for Single Service Layer Architecture
"""

from .chat_endpoints import router as chat_router
from .vote_endpoints import router as vote_router

__all__ = ["chat_router", "vote_router"]
