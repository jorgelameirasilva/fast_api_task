"""
Authentication module for Single Service Layer Architecture
"""

from .dependencies import get_current_user, AuthUser

__all__ = ["get_current_user", "AuthUser"]
