"""Chat API routes"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.api.dependencies.auth import RequireAuth

logger = logging.getLogger(__name__)

router = APIRouter()

# Global service instance
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session_id: Optional[str] = Query(
        None, description="Session ID for conversation history"
    ),
    auth_claims: Dict[str, Any] = RequireAuth,
) -> ChatResponse:
    """
    Chat endpoint with session management support

    Requires Bearer token authentication
    If session_id is provided, conversation history will be loaded and new messages saved
    """
    try:
        logger.info(
            f"Chat request received with {len(request.messages)} messages, session_id: {session_id}"
        )

        # Process chat request using service with session management
        if session_id:
            result = await chat_service.process_chat_with_session(
                request, auth_claims, session_id
            )
        else:
            result = await chat_service.process_chat(request, auth_claims)

        # Handle streaming vs non-streaming response
        if hasattr(result, "__aiter__"):
            # Streaming response
            async def generate_stream():
                async for chunk in result:
                    # Format as NDJSON (like original format_as_ndjson)
                    import json

                    yield json.dumps(chunk, ensure_ascii=False) + "\n"

            return StreamingResponse(
                generate_stream(),
                media_type="application/json-lines",
                headers={"Cache-Control": "no-cache"},
            )
        else:
            # Non-streaming response
            return result

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as error:
        logger.exception(f"Exception in /chat: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"The app encountered an error processing your request. Error type: {type(error).__name__}",
        )
