from fastapi import APIRouter, status, HTTPException, Query
from loguru import logger
from typing import Optional

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    AskRequest,
    AskResponse,
    VoteRequest,
    VoteResponse,
    AuthSetupResponse,
)

# Import the correct services
from app.services.chat_service import chat_service
from app.services.ask_service import ask_service
from app.services.vote_service import vote_service
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    request: ChatRequest,
    stream: bool = Query(False, description="Whether to stream the response"),
):
    """
    Handle chat conversations using approaches
    """
    logger.info("Chat endpoint called")

    try:
        # Ensure we have valid messages
        if not request.messages:
            raise ValueError("Request must contain messages")

        # Process using the approach system
        response = await chat_service.process_chat(request=request, stream=stream)

        # Log successful processing
        logger.info(
            f"Chat processed successfully using approach: {response.context.get('approach_used', 'unknown')}"
        )

        return response

    except ValueError as e:
        logger.error(f"Chat validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
async def ask(
    request: AskRequest,
    stream: bool = Query(False, description="Whether to stream the response"),
):
    """
    Handle user queries using approaches
    """
    logger.info(f"Ask endpoint called with query: {request.user_query[:50]}...")

    try:
        # Validate request
        if not request.user_query or not request.user_query.strip():
            raise ValueError("User query cannot be empty")

        # Process using the approach system
        response = await ask_service.process_ask(request, stream=stream)

        # Log successful processing
        logger.info(
            f"Ask processed successfully using approach: {response.context.get('approach_used', 'unknown')}"
        )

        return response

    except ValueError as e:
        logger.error(f"Ask validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ask processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/vote", response_model=VoteResponse, status_code=status.HTTP_200_OK)
async def vote(request: VoteRequest):
    """
    Handle user feedback/voting on responses
    """
    logger.info(f"Vote endpoint called: upvote={request.upvote}")
    try:
        response = await vote_service.process_vote(request)
        return response
    except ValueError as e:
        logger.error(f"Vote validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Vote processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/auth_setup", response_model=AuthSetupResponse, status_code=status.HTTP_200_OK
)
async def auth_setup():
    """
    Get authentication setup configuration
    """
    logger.info("Auth setup endpoint called")
    try:
        response = await auth_service.get_auth_setup()
        return response
    except Exception as e:
        logger.error(f"Auth setup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
