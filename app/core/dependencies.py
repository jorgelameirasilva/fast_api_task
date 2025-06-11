"""
Core Dependencies Module
Manages service instances and business logic dependencies
"""

from functools import lru_cache

from app.services.chat_service import ChatService
from app.services.session_service import SessionService
from app.services.response_generator import ResponseGenerator


# Service Singletons (FastAPI recommended pattern)
@lru_cache()
def get_session_service() -> SessionService:
    """Get singleton session service instance"""
    return SessionService()


@lru_cache()
def get_response_generator() -> ResponseGenerator:
    """Get singleton response generator instance"""
    return ResponseGenerator()


@lru_cache()
def get_chat_service() -> ChatService:
    """Get singleton chat service instance with proper dependency injection"""
    return ChatService(
        session_service=get_session_service(),
        response_generator=get_response_generator(),
    )
