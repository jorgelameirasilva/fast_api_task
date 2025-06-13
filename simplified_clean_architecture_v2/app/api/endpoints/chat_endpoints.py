"""
Chat API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Dict, List, Optional
import json
from loguru import logger

from app.auth.dependencies import get_current_user, AuthUser
from app.services.application.chat_application_service import (
    ChatApplicationService,
    ChatRequest,
    ChatResponse,
)


router = APIRouter()

# Initialize application service
chat_service = ChatApplicationService()


@router.post("/message", response_model=Dict)
async def send_chat_message(
    message: str,
    session_id: Optional[str] = None,
    use_search: bool = True,
    temperature: float = 0.7,
    current_user: AuthUser = Depends(get_current_user),
):
    """Send a chat message and get response"""

    try:
        request = ChatRequest(
            message=message,
            session_id=session_id,
            use_search=use_search,
            temperature=temperature,
        )

        response = await chat_service.process_chat_message(request, current_user)

        return {
            "success": True,
            "data": {
                "message": response.message,
                "session_id": response.session_id,
                "message_id": response.message_id,
                "timestamp": response.timestamp.isoformat(),
                "context_used": response.context_used,
                "context_sources": response.context_sources,
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/message/stream")
async def send_chat_message_stream(
    message: str,
    session_id: Optional[str] = None,
    use_search: bool = True,
    temperature: float = 0.7,
    current_user: AuthUser = Depends(get_current_user),
):
    """Send a chat message and get streaming response"""

    try:
        request = ChatRequest(
            message=message,
            session_id=session_id,
            use_search=use_search,
            temperature=temperature,
        )

        async def generate_stream():
            try:
                async for chunk in chat_service.process_streaming_chat(
                    request, current_user
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"

                # Send end marker
                yield f"data: {json.dumps({'type': 'end'})}\n\n"

            except Exception as e:
                logger.error(f"Error in streaming chat: {e}")
                error_chunk = {
                    "type": "error",
                    "content": f"An error occurred: {str(e)}",
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error in streaming chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/sessions", response_model=Dict)
async def get_user_sessions(current_user: AuthUser = Depends(get_current_user)):
    """Get all chat sessions for the current user"""

    try:
        sessions = await chat_service.get_user_sessions(current_user)

        return {"success": True, "data": {"sessions": sessions, "count": len(sessions)}}

    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/sessions/{session_id}", response_model=Dict)
async def get_session_history(
    session_id: str, current_user: AuthUser = Depends(get_current_user)
):
    """Get chat history for a specific session"""

    try:
        history = await chat_service.get_session_history(session_id, current_user)

        return {"success": True, "data": history}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/sessions/{session_id}", response_model=Dict)
async def delete_session(
    session_id: str, current_user: AuthUser = Depends(get_current_user)
):
    """Delete a chat session"""

    try:
        success = await chat_service.delete_session(session_id, current_user)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        return {"success": True, "message": "Session deleted successfully"}

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/health", response_model=Dict)
async def chat_health_check():
    """Health check for chat service"""

    try:
        # Basic health check
        return {
            "service": "chat",
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
        }

    except Exception as e:
        logger.error(f"Chat health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service unhealthy",
        )
