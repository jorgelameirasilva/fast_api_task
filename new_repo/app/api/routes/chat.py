"""
Chat API Routes - Thin HTTP layer following SOLID principles
Single Responsibility: Handle HTTP requests and delegate to business services
"""

import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies.auth import get_current_user
from app.schemas.chat import ChatRequest
from app.orchestrators.chat_orchestrator import chat_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Chat endpoint - Just call orchestrator like old design
    """
    try:
        # Just call orchestrator and return result
        return await chat_orchestrator.process_chat_request(request, current_user)
    except Exception as error:
        logger.error(f"Chat endpoint error: {error}")
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/sessions")
async def get_sessions(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Get user's active sessions
    """
    try:
        return await chat_orchestrator.get_user_sessions(current_user)
    except Exception as error:
        logger.error(f"Get sessions error: {error}")
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/sessions/{session_id}/messages")
async def get_conversation(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Get conversation history for a session
    """
    try:
        return await chat_orchestrator.get_conversation_history(
            session_id, current_user
        )
    except Exception as error:
        logger.error(f"Get conversation error: {error}")
        raise HTTPException(status_code=500, detail=str(error))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Delete a session
    """
    try:
        return await chat_orchestrator.delete_session(session_id, current_user)
    except Exception as error:
        logger.error(f"Delete session error: {error}")
        raise HTTPException(status_code=500, detail=str(error))
