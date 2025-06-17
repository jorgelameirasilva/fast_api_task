"""Session management API routes"""

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.session import Session, SessionCreateRequest, SessionResponse
from app.services.session_manager import session_manager
from app.api.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> SessionResponse:
    """Create a new chat session"""
    try:
        user_id = current_user.get("oid", "anonymous")

        session = await session_manager.create_session(
            user_id=user_id, context=request.context
        )

        logger.info(f"Created session {session.id} for user {user_id}")
        return SessionResponse(session=session, message="Session created successfully")

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions", response_model=list[Session])
async def list_sessions(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[Session]:
    """List user's chat sessions"""
    try:
        user_id = current_user.get("oid", "anonymous")
        sessions = await session_manager.get_user_sessions(user_id)

        logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
        return sessions

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/sessions/{session_id}", response_model=Session)
async def get_session(
    session_id: str, current_user: dict[str, Any] = Depends(get_current_user)
) -> Session:
    """Get a specific chat session"""
    try:
        user_id = current_user.get("oid", "anonymous")
        session = await session_manager.get_session(session_id, user_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info(f"Retrieved session {session_id} for user {user_id}")
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, current_user: dict[str, Any] = Depends(get_current_user)
) -> JSONResponse:
    """Delete a session"""
    try:
        user_id = current_user.get("oid", "anonymous")
        success = await session_manager.delete_session(session_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info(f"Deleted session {session_id} for user {user_id}")
        return JSONResponse(content={"message": "Session deleted successfully"})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")
