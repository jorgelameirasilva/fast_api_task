from typing import Any, Dict, Optional
from fastapi import status


class CustomException(Exception):
    code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "Internal server error"
    details: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if message:
            self.message = message
        if code:
            self.code = code
        if details:
            self.details = details


class NotFoundException(CustomException):
    code = status.HTTP_404_NOT_FOUND
    message = "Resource not found"


class BadRequestException(CustomException):
    code = status.HTTP_400_BAD_REQUEST
    message = "Bad request"

class DatabaseException(CustomException):
    code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Database error"
