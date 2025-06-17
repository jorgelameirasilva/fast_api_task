"""Vote API routes"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.models.vote import VoteRequest, VoteResponse
from app.services.vote_service import VoteService
from app.api.dependencies.auth import RequireAuth

logger = logging.getLogger(__name__)

router = APIRouter()

# Global service instance
vote_service = VoteService()


@router.post("/vote", response_model=VoteResponse, status_code=200)
async def vote(
    request: VoteRequest,
    auth_claims: Dict[str, Any] = RequireAuth,
) -> VoteResponse:
    """
    Vote endpoint - replicates the exact behavior of the original /vote route

    Requires Bearer token authentication
    """
    try:
        logger.info("Vote request received")

        # Process vote request using service
        result = await vote_service.process_vote(request)

        logger.info("Vote processed successfully")
        return result

    except ValidationError as e:
        # Handle Pydantic validation errors (converts to 400 errors like original)
        logger.warning(f"Validation error in /vote: {e}")

        # Extract the first error message to match original format
        if e.errors():
            error_detail = e.errors()[0]["msg"]
        else:
            error_detail = "Validation error"

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"error": error_detail}
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as error:
        logger.exception(f"Exception in /vote: {error}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"The app encountered an error processing your request. Error type: {type(error).__name__}"
            },
        )
