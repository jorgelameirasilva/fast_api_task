"""Vote service for handling vote business logic"""

import logging
from typing import Dict, Any, Union

from app.core.config import settings
from app.models.vote import VoteRequest, VoteResponse

logger = logging.getLogger(__name__)


class VoteService:
    """Service for handling vote operations"""

    def __init__(self):
        # Initialize logging with same format as original
        self.logger = logging.getLogger("chatbot/chatbot-logs.log")

    async def process_vote(self, request: VoteRequest) -> VoteResponse:
        """
        Process vote request and return response

        This replicates the exact behavior of the original /vote endpoint
        """
        try:
            # Extract and process request data (exactly like original)
            user_query = request.user_query
            chatbot_response = request.chatbot_response
            count = request.count
            upvote = request.upvote
            downvote = request.downvote

            # Process chatbot_response if it's a string and not empty/None
            if (
                isinstance(chatbot_response, str)
                and chatbot_response != ""
                and chatbot_response is not None
            ):
                chatbot_response = chatbot_response.replace("\n", "")

            # Record upvote (exactly like original)
            if upvote == 1:
                if count == 1:
                    self.logger.info(
                        "UPVOTE_RECORDED",
                        extra={
                            "user_query": user_query,
                            "chatbot_response": chatbot_response,
                        },
                    )
                elif count == -1:
                    self.logger.info(
                        "UPVOTE_REMOVED",
                        extra={
                            "user_query": user_query,
                            "chatbot_response": chatbot_response,
                        },
                    )

            # Record downvote (exactly like original)
            elif downvote == 1:
                # Process reason_multiple_choice
                reason_multiple_choice = request.reason_multiple_choice
                if isinstance(reason_multiple_choice, str):
                    reason_multiple_choice = reason_multiple_choice.strip().replace(
                        "\n", ""
                    )
                elif reason_multiple_choice == {}:
                    reason_multiple_choice = ""

                # Process additional_comments
                additional_comments = request.additional_comments
                if isinstance(additional_comments, str):
                    additional_comments = additional_comments.strip().replace("\n", "")
                elif additional_comments == {}:
                    additional_comments = ""

                if count == 1:
                    self.logger.info(
                        "DOWNVOTE_RECORDED",
                        extra={
                            "user_query": user_query,
                            "chatbot_response": chatbot_response,
                            "reason_multiple_choice": reason_multiple_choice,
                            "additional_comments": additional_comments,
                        },
                    )
                elif count == -1:
                    self.logger.info(
                        "DOWNVOTE_REMOVED",
                        extra={
                            "user_query": user_query,
                            "chatbot_response": chatbot_response,
                            "reason_multiple_choice": reason_multiple_choice,
                            "additional_comments": additional_comments,
                        },
                    )

            # Return response in exact same format as original
            return VoteResponse(
                user_query=user_query,
                message=chatbot_response,  # Note: renamed from chatbot_response to message
                upvote=upvote,
                downvote=downvote,
                count=count,
            )

        except Exception as e:
            logger.error(f"Vote processing failed: {str(e)}")
            raise
