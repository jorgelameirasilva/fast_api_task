"""Session management API routes"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.session import (
    ChatSession,
    SessionSummary,
    CreateSessionRequest,
    UpdateSessionRequest,
    AddMessageRequest,
    SessionSearchRequest,
)
from app.services.cosmos_service import cosmos_session_service
from app.api.dependencies.auth import RequireAuth

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sessions", response_model=ChatSession)
async def create_session(
    request: CreateSessionRequest, auth_claims: Dict[str, Any] = RequireAuth
) -> ChatSession:
    """Create a new chat session"""
    try:
        user_id = auth_claims.get("preferred_username") or auth_claims.get(
            "sub", "anonymous"
        )

        session = await cosmos_session_service.create_session(
            user_id=user_id,
            title=request.title,
            context=request.context,
            max_messages=request.max_messages,
        )

        logger.info(f"Created session {session.id} for user {user_id}")
        return session

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions", response_model=List[SessionSummary])
async def list_sessions(
    is_active: bool = Query(default=True, description="Filter by active status"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    auth_claims: Dict[str, Any] = RequireAuth,
) -> List[SessionSummary]:
    """List user's chat sessions"""
    try:
        user_id = auth_claims.get("preferred_username") or auth_claims.get(
            "sub", "anonymous"
        )

        sessions = await cosmos_session_service.list_user_sessions(
            user_id=user_id, is_active=is_active, limit=limit, offset=offset
        )

        logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
        return sessions

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(
    session_id: str, auth_claims: Dict[str, Any] = RequireAuth
) -> ChatSession:
    """Get a specific chat session"""
    try:
        user_id = auth_claims.get("preferred_username") or auth_claims.get(
            "sub", "anonymous"
        )

        session = await cosmos_session_service.get_session(session_id, user_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Ensure user can only access their own sessions
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        logger.info(f"Retrieved session {session_id} for user {user_id}")
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.put("/sessions/{session_id}", response_model=ChatSession)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    auth_claims: Dict[str, Any] = RequireAuth,
) -> ChatSession:
    """Update session metadata"""
    try:
        user_id = auth_claims.get("preferred_username") or auth_claims.get(
            "sub", "anonymous"
        )

        session = await cosmos_session_service.get_session(session_id, user_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Ensure user can only update their own sessions
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update fields if provided
        if request.title is not None:
            session.title = request.title
        if request.context is not None:
            session.context.update(request.context)
        if request.is_active is not None:
            session.is_active = request.is_active
        if request.max_messages is not None:
            session.max_messages = request.max_messages

        updated_session = await cosmos_session_service.update_session(session)

        logger.info(f"Updated session {session_id} for user {user_id}")
        return updated_session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session")


@router.post("/sessions/{session_id}/messages", response_model=ChatSession)
async def add_message_to_session(
    session_id: str,
    request: AddMessageRequest,
    auth_claims: Dict[str, Any] = RequireAuth,
) -> ChatSession:
    """Add a message to a session"""
    try:
        user_id = auth_claims.get("preferred_username") or auth_claims.get(
            "sub", "anonymous"
        )

        updated_session = await cosmos_session_service.add_message_to_session(
            session_id=session_id,
            user_id=user_id,
            message=request.message,
            update_context=request.update_context,
        )

        if not updated_session:
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info(f"Added message to session {session_id} for user {user_id}")
        return updated_session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add message to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add message")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, auth_claims: Dict[str, Any] = RequireAuth
) -> JSONResponse:
    """Delete (deactivate) a session"""
    try:
        user_id = auth_claims.get("preferred_username") or auth_claims.get(
            "sub", "anonymous"
        )

        success = await cosmos_session_service.delete_session(session_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info(f"Deleted session {session_id} for user {user_id}")
        return JSONResponse(content={"message": "Session deleted successfully"})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.post("/sessions/search", response_model=List[SessionSummary])
async def search_sessions(
    request: SessionSearchRequest, auth_claims: Dict[str, Any] = RequireAuth
) -> List[SessionSummary]:
    """Search sessions with advanced filtering"""
    try:
        user_id = auth_claims.get("preferred_username") or auth_claims.get(
            "sub", "anonymous"
        )

        # Ensure user can only search their own sessions
        request.user_id = user_id

        sessions = await cosmos_session_service.search_sessions(request)

        logger.info(f"Search returned {len(sessions)} sessions for user {user_id}")
        return sessions

    except Exception as e:
        logger.error(f"Failed to search sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to search sessions")


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = Query(default="json", regex="^(json|txt)$"),
    auth_claims: Dict[str, Any] = RequireAuth,
):
    """Export session data in different formats"""
    try:
        user_id = auth_claims.get("preferred_username") or auth_claims.get(
            "sub", "anonymous"
        )

        session = await cosmos_session_service.get_session(session_id, user_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Ensure user can only export their own sessions
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        if format == "json":
            return JSONResponse(content=session.model_dump())
        elif format == "txt":
            # Create a readable text format
            lines = [
                f"Session: {session.title or session.id}",
                f"Created: {session.created_at}",
                f"Updated: {session.updated_at}",
                f"Messages: {len(session.messages)}",
                "",
                "Conversation History:",
                "=" * 50,
            ]

            for i, message in enumerate(session.messages, 1):
                lines.append(f"\n{i}. {message.role.upper()}: {message.content}")

            content = "\n".join(lines)

            from fastapi.responses import PlainTextResponse

            return PlainTextResponse(
                content=content,
                headers={
                    "Content-Disposition": f"attachment; filename=session_{session_id}.txt"
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export session")
