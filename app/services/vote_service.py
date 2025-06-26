"""Vote service for handling voting business logic"""

import logging
from typing import Any
from app.models.vote import VoteRequest, VoteResponse

logger = logging.getLogger(__name__)


class VoteService:
    """Service for handling vote operations - matches original app.py functionality"""

    async def process_vote(self, request: VoteRequest) -> VoteResponse:
        """
        Process a vote request - just log and return response like original app.py

        Args:
            request: VoteRequest object containing vote information

        Returns:
            VoteResponse: The vote response to return to client
        """
        try:
            # Log the vote exactly like original app.py
            if request.upvote == 1:
                if request.count == 1:
                    logger.info(
                        "UPVOTE_RECORDED",
                        extra={
                            "user_query": request.user_query,
                            "chatbot_response": request.chatbot_response,
                        },
                    )
                elif request.count == -1:
                    logger.info(
                        "UPVOTE_REMOVED",
                        extra={
                            "user_query": request.user_query,
                            "chatbot_response": request.chatbot_response,
                        },
                    )
            elif request.downvote == 1:
                if request.count == 1:
                    logger.info(
                        "DOWNVOTE_RECORDED",
                        extra={
                            "user_query": request.user_query,
                            "chatbot_response": request.chatbot_response,
                            "reason_multiple_choice": request.reason_multiple_choice,
                            "additional_comments": request.additional_comments,
                        },
                    )
                elif request.count == -1:
                    logger.info(
                        "DOWNVOTE_REMOVED",
                        extra={
                            "user_query": request.user_query,
                            "chatbot_response": request.chatbot_response,
                            "reason_multiple_choice": request.reason_multiple_choice,
                            "additional_comments": request.additional_comments,
                        },
                    )

            # Return the response exactly like original app.py
            return VoteResponse(
                user_query=request.user_query,
                chatbot_response=request.chatbot_response,
                upvote=request.upvote,
                downvote=request.downvote,
                count=request.count,
            )

        except Exception as e:
            logger.error(f"Error processing vote: {str(e)}")
            raise


# Global instance
vote_service = VoteService()
