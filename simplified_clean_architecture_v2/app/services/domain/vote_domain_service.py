"""
Vote Domain Service - Pure business logic for voting functionality
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from loguru import logger


class VoteType(Enum):
    """Vote types"""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


@dataclass
class Vote:
    """Vote domain model"""

    id: str
    user_id: str
    message_id: str
    session_id: str
    vote_type: VoteType
    feedback: Optional[str] = None
    timestamp: datetime = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class VoteStats:
    """Vote statistics"""

    total_votes: int
    thumbs_up_count: int
    thumbs_down_count: int
    satisfaction_rate: float
    common_feedback_themes: List[str]


@dataclass
class VoteSummary:
    """Vote summary for a specific message or session"""

    message_id: str
    votes: List[Vote]
    stats: VoteStats
    user_vote: Optional[Vote] = None  # Current user's vote if any


class VoteDomainService:
    """Pure business logic for voting operations"""

    def __init__(self):
        self.max_feedback_length = 1000
        self.min_feedback_length = 5

    def validate_vote(
        self, vote_type: str, feedback: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """Validate vote data"""

        # Validate vote type
        try:
            VoteType(vote_type)
        except ValueError:
            return (
                False,
                f"Invalid vote type: {vote_type}. Must be 'thumbs_up' or 'thumbs_down'",
            )

        # Validate feedback if provided
        if feedback is not None:
            if len(feedback.strip()) < self.min_feedback_length:
                return (
                    False,
                    f"Feedback must be at least {self.min_feedback_length} characters",
                )

            if len(feedback) > self.max_feedback_length:
                return (
                    False,
                    f"Feedback must not exceed {self.max_feedback_length} characters",
                )

            # Check for potentially harmful content
            harmful_patterns = ["<script", "javascript:", "eval(", "exec("]
            if any(pattern in feedback.lower() for pattern in harmful_patterns):
                return False, "Feedback contains potentially harmful content"

        return True, None

    def create_vote(
        self,
        vote_id: str,
        user_id: str,
        message_id: str,
        session_id: str,
        vote_type: str,
        feedback: Optional[str] = None,
    ) -> Vote:
        """Create a new vote"""

        return Vote(
            id=vote_id,
            user_id=user_id,
            message_id=message_id,
            session_id=session_id,
            vote_type=VoteType(vote_type),
            feedback=feedback.strip() if feedback else None,
            timestamp=datetime.utcnow(),
        )

    def can_user_vote(
        self, user_id: str, message_id: str, existing_votes: List[Vote]
    ) -> tuple[bool, Optional[str]]:
        """Check if user can vote on a message"""

        # Check if user already voted on this message
        user_votes = [
            v
            for v in existing_votes
            if v.user_id == user_id and v.message_id == message_id
        ]

        if user_votes:
            return False, "User has already voted on this message"

        return True, None

    def can_user_update_vote(
        self, user_id: str, vote_id: str, existing_votes: List[Vote]
    ) -> tuple[bool, Optional[str], Optional[Vote]]:
        """Check if user can update a specific vote"""

        # Find the vote
        vote = next((v for v in existing_votes if v.id == vote_id), None)

        if not vote:
            return False, "Vote not found", None

        if vote.user_id != user_id:
            return False, "User can only update their own votes", None

        # Check if vote is not too old (allow updates within 24 hours)
        hours_since_vote = (datetime.utcnow() - vote.timestamp).total_seconds() / 3600
        if hours_since_vote > 24:
            return False, "Vote is too old to be updated (max 24 hours)", vote

        return True, None, vote

    def update_vote(
        self,
        original_vote: Vote,
        new_vote_type: Optional[str] = None,
        new_feedback: Optional[str] = None,
    ) -> Vote:
        """Update an existing vote"""

        # Create updated vote
        updated_vote = Vote(
            id=original_vote.id,
            user_id=original_vote.user_id,
            message_id=original_vote.message_id,
            session_id=original_vote.session_id,
            vote_type=(
                VoteType(new_vote_type) if new_vote_type else original_vote.vote_type
            ),
            feedback=new_feedback.strip() if new_feedback else original_vote.feedback,
            timestamp=datetime.utcnow(),  # Update timestamp
            metadata=original_vote.metadata,
        )

        return updated_vote

    def calculate_vote_stats(self, votes: List[Vote]) -> VoteStats:
        """Calculate statistics from votes"""

        if not votes:
            return VoteStats(
                total_votes=0,
                thumbs_up_count=0,
                thumbs_down_count=0,
                satisfaction_rate=0.0,
                common_feedback_themes=[],
            )

        thumbs_up_count = sum(1 for v in votes if v.vote_type == VoteType.THUMBS_UP)
        thumbs_down_count = sum(1 for v in votes if v.vote_type == VoteType.THUMBS_DOWN)

        satisfaction_rate = thumbs_up_count / len(votes) if votes else 0.0

        # Extract common feedback themes (simple keyword analysis)
        feedback_themes = self._extract_feedback_themes(votes)

        return VoteStats(
            total_votes=len(votes),
            thumbs_up_count=thumbs_up_count,
            thumbs_down_count=thumbs_down_count,
            satisfaction_rate=satisfaction_rate,
            common_feedback_themes=feedback_themes,
        )

    def get_vote_summary(
        self, message_id: str, all_votes: List[Vote], user_id: Optional[str] = None
    ) -> VoteSummary:
        """Get vote summary for a specific message"""

        # Filter votes for this message
        message_votes = [v for v in all_votes if v.message_id == message_id]

        # Calculate stats
        stats = self.calculate_vote_stats(message_votes)

        # Find user's vote if user_id provided
        user_vote = None
        if user_id:
            user_vote = next((v for v in message_votes if v.user_id == user_id), None)

        return VoteSummary(
            message_id=message_id, votes=message_votes, stats=stats, user_vote=user_vote
        )

    def should_request_feedback(self, vote_type: VoteType) -> bool:
        """Determine if feedback should be requested based on vote type"""

        # Always encourage feedback for negative votes
        if vote_type == VoteType.THUMBS_DOWN:
            return True

        # Sometimes request feedback for positive votes (for improvement)
        return False

    def get_feedback_prompt(self, vote_type: VoteType) -> str:
        """Get appropriate feedback prompt based on vote type"""

        if vote_type == VoteType.THUMBS_DOWN:
            return "What could be improved about this response?"
        else:
            return "What did you find most helpful about this response?"

    def _extract_feedback_themes(self, votes: List[Vote]) -> List[str]:
        """Extract common themes from feedback (simple implementation)"""

        feedback_texts = [v.feedback for v in votes if v.feedback]

        if not feedback_texts:
            return []

        # Simple keyword extraction
        common_words = {}
        for feedback in feedback_texts:
            words = feedback.lower().split()
            for word in words:
                if len(word) > 3:  # Only consider words longer than 3 characters
                    common_words[word] = common_words.get(word, 0) + 1

        # Get most common themes
        sorted_themes = sorted(common_words.items(), key=lambda x: x[1], reverse=True)
        return [theme[0] for theme in sorted_themes[:5]]  # Top 5 themes

    def is_vote_recent(self, vote: Vote, hours: int = 1) -> bool:
        """Check if vote is recent (within specified hours)"""

        time_diff = datetime.utcnow() - vote.timestamp
        return time_diff.total_seconds() < (hours * 3600)

    def get_user_voting_pattern(self, user_id: str, all_votes: List[Vote]) -> Dict:
        """Analyze user's voting pattern"""

        user_votes = [v for v in all_votes if v.user_id == user_id]

        if not user_votes:
            return {
                "total_votes": 0,
                "thumbs_up_ratio": 0.0,
                "provides_feedback_ratio": 0.0,
                "most_active_period": None,
            }

        thumbs_up_count = sum(
            1 for v in user_votes if v.vote_type == VoteType.THUMBS_UP
        )
        feedback_count = sum(1 for v in user_votes if v.feedback)

        return {
            "total_votes": len(user_votes),
            "thumbs_up_ratio": thumbs_up_count / len(user_votes),
            "provides_feedback_ratio": feedback_count / len(user_votes),
            "most_active_period": self._get_most_active_period(user_votes),
        }

    def _get_most_active_period(self, votes: List[Vote]) -> Optional[str]:
        """Get the most active voting period for a user"""

        if not votes:
            return None

        # Group by hour of day
        hour_counts = {}
        for vote in votes:
            hour = vote.timestamp.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        # Find most active hour
        most_active_hour = max(hour_counts.items(), key=lambda x: x[1])[0]

        # Convert to period description
        if 6 <= most_active_hour < 12:
            return "morning"
        elif 12 <= most_active_hour < 18:
            return "afternoon"
        elif 18 <= most_active_hour < 22:
            return "evening"
        else:
            return "night"
