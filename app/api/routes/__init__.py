"""API routes package - Centralized router"""

from fastapi import APIRouter

from . import chat, vote

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(vote.router, tags=["vote"])

__all__ = ["api_router", "chat", "vote"]
