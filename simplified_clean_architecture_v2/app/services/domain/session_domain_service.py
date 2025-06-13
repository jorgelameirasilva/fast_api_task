"""
Session Domain Service - Pure business logic for session management
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid
from loguru import logger

from .chat_domain_service import ChatSession, ChatMessage


@dataclass
class SessionMetadata:
    """Session metadata"""

    title: Optional[str] = None
    tags: List[str] = None
    last_activity: datetime = None
    message_count: int = 0
    total_duration: timedelta = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()
        if self.total_duration is None:
            self.total_duration = timedelta()


class SessionDomainService:
    """Pure business logic for session management"""

    def __init__(self):
        self.max_session_duration_hours = 24
        self.max_sessions_per_user = 50
        self.session_cleanup_threshold_days = 30
        self.max_session_title_length = 100

    def create_new_session(
        self, user_id: str, session_id: Optional[str] = None
    ) -> ChatSession:
        """Create a new chat session"""

        if not session_id:
            session_id = str(uuid.uuid4())

        now = datetime.utcnow()

        return ChatSession(
            session_id=session_id,
            user_id=user_id,
            messages=[],
            created_at=now,
            updated_at=now,
            context={},
        )

    def is_session_valid(self, session: ChatSession) -> tuple[bool, Optional[str]]:
        """Check if a session is valid and active"""

        if not session:
            return False, "Session not found"

        # Check if session is too old
        session_age = datetime.utcnow() - session.created_at
        if session_age.total_seconds() > (self.max_session_duration_hours * 3600):
            return (
                False,
                f"Session expired (max {self.max_session_duration_hours} hours)",
            )

        return True, None

    def can_user_access_session(
        self, user_id: str, session: ChatSession
    ) -> tuple[bool, Optional[str]]:
        """Check if user can access a specific session"""

        if session.user_id != user_id:
            return False, "User can only access their own sessions"

        return True, None

    def generate_session_title(self, messages: List[ChatMessage]) -> str:
        """Generate an appropriate title for the session based on messages"""

        if not messages:
            return "New Chat Session"

        # Find the first user message
        first_user_message = next((msg for msg in messages if msg.role == "user"), None)

        if not first_user_message:
            return "New Chat Session"

        # Use first 50 characters of the first user message
        title = first_user_message.content[:50].strip()

        # Clean up the title
        title = title.replace("\n", " ").replace("\r", " ")
        while "  " in title:  # Remove multiple spaces
            title = title.replace("  ", " ")

        # Add ellipsis if truncated
        if len(first_user_message.content) > 50:
            title += "..."

        return title or "New Chat Session"

    def update_session_metadata(self, session: ChatSession) -> SessionMetadata:
        """Update and return session metadata"""

        metadata = SessionMetadata(
            title=self.generate_session_title(session.messages),
            last_activity=session.updated_at,
            message_count=len(session.messages),
            total_duration=session.updated_at - session.created_at,
        )

        # Generate tags based on message content (simple implementation)
        metadata.tags = self._generate_session_tags(session.messages)

        return metadata

    def should_cleanup_session(
        self, session: ChatSession, user_session_count: int
    ) -> tuple[bool, str]:
        """Determine if a session should be cleaned up"""

        # Clean up if session is too old
        days_old = (datetime.utcnow() - session.created_at).days
        if days_old > self.session_cleanup_threshold_days:
            return (
                True,
                f"Session older than {self.session_cleanup_threshold_days} days",
            )

        # Clean up if user has too many sessions (keep most recent)
        if user_session_count > self.max_sessions_per_user:
            return (
                True,
                f"User has too many sessions (max {self.max_sessions_per_user})",
            )

        # Clean up empty sessions older than 1 day
        if not session.messages and days_old > 1:
            return True, "Empty session older than 1 day"

        return False, ""

    def get_session_summary(self, session: ChatSession) -> Dict:
        """Get a summary of the session"""

        if not session.messages:
            return {
                "session_id": session.session_id,
                "status": "empty",
                "created_at": session.created_at.isoformat(),
                "message_count": 0,
                "duration": "0 minutes",
            }

        # Calculate session statistics
        user_messages = [msg for msg in session.messages if msg.role == "user"]
        assistant_messages = [
            msg for msg in session.messages if msg.role == "assistant"
        ]

        duration = session.updated_at - session.created_at
        duration_minutes = int(duration.total_seconds() / 60)

        # Calculate average response time (if we have timestamps)
        avg_response_time = self._calculate_average_response_time(session.messages)

        return {
            "session_id": session.session_id,
            "title": self.generate_session_title(session.messages),
            "status": "active",
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": len(session.messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "duration": f"{duration_minutes} minutes",
            "avg_response_time": avg_response_time,
            "tags": self._generate_session_tags(session.messages),
        }

    def merge_sessions(
        self, primary_session: ChatSession, secondary_session: ChatSession
    ) -> ChatSession:
        """Merge two sessions (used for session consolidation)"""

        # Combine messages and sort by timestamp
        all_messages = primary_session.messages + secondary_session.messages
        all_messages.sort(key=lambda m: m.timestamp)

        # Update the primary session
        primary_session.messages = all_messages
        primary_session.updated_at = datetime.utcnow()

        # Update context if needed
        if secondary_session.context:
            if not primary_session.context:
                primary_session.context = {}
            primary_session.context.update(secondary_session.context)

        return primary_session

    def validate_session_data(self, session_data: Dict) -> tuple[bool, Optional[str]]:
        """Validate session data structure"""

        required_fields = ["session_id", "user_id", "created_at"]

        for field in required_fields:
            if field not in session_data:
                return False, f"Missing required field: {field}"

        # Validate session_id format (should be UUID-like)
        session_id = session_data.get("session_id", "")
        if not session_id or len(session_id) < 10:
            return False, "Invalid session_id format"

        # Validate user_id
        user_id = session_data.get("user_id", "")
        if not user_id or len(user_id) < 3:
            return False, "Invalid user_id"

        return True, None

    def _generate_session_tags(self, messages: List[ChatMessage]) -> List[str]:
        """Generate tags based on message content (simple implementation)"""

        if not messages:
            return []

        # Simple keyword-based tagging
        tag_keywords = {
            "technical": [
                "code",
                "programming",
                "software",
                "development",
                "api",
                "database",
            ],
            "help": ["help", "how to", "guide", "tutorial", "instructions"],
            "question": ["what", "why", "how", "when", "where", "which"],
            "problem": ["error", "issue", "problem", "bug", "fix", "troubleshoot"],
            "creative": ["create", "design", "write", "generate", "make"],
            "analysis": ["analyze", "compare", "evaluate", "review", "assess"],
        }

        tags = set()

        # Combine all message content
        all_content = " ".join([msg.content.lower() for msg in messages])

        # Check for tag keywords
        for tag, keywords in tag_keywords.items():
            if any(keyword in all_content for keyword in keywords):
                tags.add(tag)

        # Add length-based tags
        if len(messages) > 20:
            tags.add("long-conversation")
        elif len(messages) < 5:
            tags.add("short-conversation")

        return list(tags)[:5]  # Limit to 5 tags

    def _calculate_average_response_time(
        self, messages: List[ChatMessage]
    ) -> Optional[str]:
        """Calculate average response time between user and assistant messages"""

        if len(messages) < 2:
            return None

        response_times = []

        for i in range(len(messages) - 1):
            current_msg = messages[i]
            next_msg = messages[i + 1]

            # Look for user -> assistant pattern
            if current_msg.role == "user" and next_msg.role == "assistant":
                time_diff = next_msg.timestamp - current_msg.timestamp
                response_times.append(time_diff.total_seconds())

        if not response_times:
            return None

        avg_seconds = sum(response_times) / len(response_times)

        if avg_seconds < 60:
            return f"{int(avg_seconds)} seconds"
        else:
            return f"{int(avg_seconds / 60)} minutes"

    def get_sessions_requiring_cleanup(
        self, all_sessions: List[ChatSession], user_id: str
    ) -> List[ChatSession]:
        """Get list of sessions that should be cleaned up for a user"""

        user_sessions = [s for s in all_sessions if s.user_id == user_id]

        # Sort by creation date (oldest first)
        user_sessions.sort(key=lambda s: s.created_at)

        cleanup_sessions = []

        for session in user_sessions:
            should_cleanup, reason = self.should_cleanup_session(
                session, len(user_sessions)
            )
            if should_cleanup:
                cleanup_sessions.append(session)

        return cleanup_sessions
