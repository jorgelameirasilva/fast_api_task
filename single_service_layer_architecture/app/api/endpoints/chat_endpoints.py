"""
Chat API Endpoints - Single Service Layer Architecture
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import asyncio
from loguru import logger

from app.auth.dependencies import get_current_user, AuthUser
from app.services.chat_service import ChatService, ChatRequest, ChatResponse


# Create service instance (in production, use dependency injection)
chat_service = ChatService()

# Create router
router = APIRouter()


# Request/Response models
class SendMessageRequest(BaseModel):
    """Request model for sending a message"""

    message: str
    session_id: Optional[str] = None
    use_search: bool = True
    temperature: float = 0.7


class SendMessageResponse(BaseModel):
    """Response model for sending a message"""

    message: str
    session_id: str
    message_id: str
    timestamp: str
    context_used: bool = False
    context_sources: List[str] = []


class SessionHistoryResponse(BaseModel):
    """Response model for session history"""

    session: Dict
    messages: List[Dict]


class UserSessionsResponse(BaseModel):
    """Response model for user sessions"""

    sessions: List[Dict]


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest, user: AuthUser = Depends(get_current_user)
):
    """
    Send a chat message and get response
    """
    try:
        # Convert request to service format
        chat_request = ChatRequest(
            message=request.message,
            session_id=request.session_id,
            use_search=request.use_search,
            temperature=request.temperature,
        )

        # Call service directly
        response = await chat_service.send_message(chat_request, user)

        # Convert response to API format
        return SendMessageResponse(
            message=response.message,
            session_id=response.session_id,
            message_id=response.message_id,
            timestamp=response.timestamp.isoformat(),
            context_used=response.context_used,
            context_sources=response.context_sources,
        )

    except ValueError as e:
        logger.error(f"Validation error in send_message: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/stream")
async def send_message_stream(
    request: SendMessageRequest, user: AuthUser = Depends(get_current_user)
):
    """
    Send a chat message with streaming response
    """
    try:
        # Convert request to service format
        chat_request = ChatRequest(
            message=request.message,
            session_id=request.session_id,
            use_search=request.use_search,
            temperature=request.temperature,
        )

        async def stream_generator():
            """Generator for streaming response"""
            try:
                async for chunk in chat_service.send_message_stream(chat_request, user):
                    # Send each chunk as Server-Sent Event
                    yield f"data: {json.dumps(chunk)}\n\n"

                # Send end marker
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Error in stream: {e}")
                error_chunk = {
                    "type": "error",
                    "content": f"An error occurred: {str(e)}",
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )

    except ValueError as e:
        logger.error(f"Validation error in send_message_stream: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in send_message_stream: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str, user: AuthUser = Depends(get_current_user)
):
    """
    Get chat session history
    """
    try:
        # Call service directly
        history = await chat_service.get_session_history(session_id, user)

        return SessionHistoryResponse(
            session=history["session"], messages=history["messages"]
        )

    except ValueError as e:
        logger.error(f"Validation error in get_session_history: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        logger.error(f"Permission error in get_session_history: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error in get_session_history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions", response_model=UserSessionsResponse)
async def get_user_sessions(user: AuthUser = Depends(get_current_user)):
    """
    Get all sessions for the current user
    """
    try:
        # Call service directly
        sessions = await chat_service.get_user_sessions(user)

        return UserSessionsResponse(sessions=sessions)

    except Exception as e:
        logger.error(f"Error in get_user_sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: AuthUser = Depends(get_current_user)):
    """
    Delete a chat session
    """
    try:
        # Call service directly
        success = await chat_service.delete_session(session_id, user)

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"message": "Session deleted successfully", "session_id": session_id}

    except PermissionError as e:
        logger.error(f"Permission error in delete_session: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error in delete_session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def chat_health():
    """Health check for chat service"""
    try:
        # Simple health check - could be expanded to test service components
        return {
            "status": "healthy",
            "service": "chat",
            "architecture": "single_service_layer",
            "components": {
                "chat_service": "✅",
                "llm_repository": "✅",
                "search_repository": "✅",
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")


@router.get("/test")
async def test_endpoint():
    """Test endpoint for development"""
    return {
        "message": "Chat service is working",
        "architecture": "single_service_layer",
        "description": "Simplest clean architecture with combined service layer",
    }
