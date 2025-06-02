"""
Services module - Contains all business logic services following SOLID principles.

Each service has a single responsibility:
- ChatService: Chat operations only
- AskService: Ask operations only
- VoteService: Voting/feedback operations only
- AuthService: Authentication operations only
- SessionService: Session management only
- ResponseGenerator: Response generation only
"""

from app.services.chat_service import chat_service, ChatService
from app.services.ask_service import ask_service, AskService
from app.services.vote_service import vote_service, VoteService
from app.services.auth_service import auth_service, AuthService
from app.services.session_service import session_service, SessionService
from app.services.response_generator import response_generator, ResponseGenerator

__all__ = [
    "chat_service",
    "ChatService",
    "ask_service",
    "AskService",
    "vote_service",
    "VoteService",
    "auth_service",
    "AuthService",
    "session_service",
    "SessionService",
    "response_generator",
    "ResponseGenerator",
]
