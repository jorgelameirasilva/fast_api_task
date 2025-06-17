"""Custom exception classes"""

from typing import Optional, Dict, Any


class ChatbotException(Exception):
    """Base exception for chatbot operations"""

    def __init__(
        self,
        message: str,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_type = error_type or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationException(ChatbotException):
    """Exception for authentication errors"""

    pass


class ChatProcessingException(ChatbotException):
    """Exception for chat processing errors"""

    pass


class VoteProcessingException(ChatbotException):
    """Exception for vote processing errors"""

    pass


class ConfigurationException(ChatbotException):
    """Exception for configuration errors"""

    pass


class ClientException(ChatbotException):
    """Exception for client-related errors"""

    pass
