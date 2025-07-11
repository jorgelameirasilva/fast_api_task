"""Simplified MongoDB service for message-based storage"""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.models.document import (
    MessageDocument,
    MessageCreateRequest,
    MessageVoteRequest,
    SessionSummary,
)
from app.services.title_service import (
    TitleGenerationService,
    SimpleTitleGenerationService,
    create_title_service,
)

logger = logging.getLogger(__name__)


class CosmosService:
    """Simple service for managing individual message documents in MongoDB"""

    def __init__(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str = "messages",
        title_service: Optional[TitleGenerationService] = None,
    ):
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.title_service = title_service or SimpleTitleGenerationService()
        self._client: Optional[MongoClient] = None
        self._collection = None

    @property
    def collection(self):
        """Lazy initialization of MongoDB collection"""
        if self._collection is None:
            if self._client is None:
                self._client = MongoClient(self.connection_string)
                logger.info("MongoDB client initialized")

            database = self._client[self.database_name]
            self._collection = database[self.collection_name]
            self._create_indexes()
        return self._collection

    def _create_indexes(self) -> None:
        """Create necessary indexes for optimal performance"""
        try:
            self._collection.create_index("user_id")
            self._collection.create_index("session_id")
            self._collection.create_index([("user_id", 1), ("session_id", 1)])
            self._collection.create_index([("session_id", 1), ("created_at", 1)])
            self._collection.create_index("is_active")
            logger.info("Database indexes created successfully")
        except PyMongoError as e:
            logger.warning(f"Failed to create indexes: {e}")

    def _to_document(self, message: MessageDocument) -> Dict[str, Any]:
        """Convert MessageDocument to MongoDB document"""
        doc = message.model_dump()
        doc["_id"] = doc.pop("id")  # Map id to _id for MongoDB
        doc["created_at"] = message.created_at.isoformat()
        doc["updated_at"] = message.updated_at.isoformat()
        if message.voted_at:
            doc["voted_at"] = message.voted_at.isoformat()
        return doc

    def _from_document(self, doc: Dict[str, Any]) -> MessageDocument:
        """Convert MongoDB document to MessageDocument"""
        doc["id"] = doc.pop("_id")  # Map _id back to id for Pydantic
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        if doc.get("voted_at"):
            doc["voted_at"] = datetime.fromisoformat(doc["voted_at"])
        return MessageDocument(**doc)

    def _generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate a session title from the first user message"""
        title = first_message.strip()
        if len(title) > max_length:
            title = title[: max_length - 3] + "..."
        return title

    async def create_message(
        self,
        request: MessageCreateRequest,
        user_id: str,
    ) -> MessageDocument:
        """Create a new message document"""

        # Generate session_id if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Check if this is a new session and generate title if needed
        title = None
        if request.session_id:
            # Existing session - get title from first message
            existing_messages = await self.get_conversation(
                session_id, user_id, limit=1
            )
            if existing_messages:
                title = existing_messages[0].title
        else:
            # New session - generate title from first user message using title service
            if request.message.role == "user":
                title = await self.title_service.generate_title(request.message.content)

        message = MessageDocument(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            title=title,
            message=request.message,
            knowledge_base=request.knowledge_base,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        try:
            document = self._to_document(message)
            self.collection.insert_one(document)
            logger.info(
                f"Created message {message.id} in session {session_id} with title: {title}"
            )
            return message
        except PyMongoError as e:
            logger.error(f"Failed to create message: {e}")
            raise

    async def get_message(
        self, message_id: str, user_id: str
    ) -> Optional[MessageDocument]:
        """Get message by ID and user ID"""
        try:
            doc = self.collection.find_one(
                {"_id": message_id, "user_id": user_id, "is_active": True}
            )
            if doc:
                return self._from_document(doc)
            return None
        except PyMongoError as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            return None

    async def get_conversation(
        self,
        session_id: str,
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[MessageDocument]:
        """Get conversation messages for a session"""
        try:
            query = {"session_id": session_id, "user_id": user_id, "is_active": True}

            cursor = self.collection.find(query).sort("created_at", 1)

            if offset > 0:
                cursor = cursor.skip(offset)
            if limit:
                cursor = cursor.limit(limit)

            messages = [self._from_document(doc) for doc in cursor]
            logger.info(f"Retrieved {len(messages)} messages from session {session_id}")
            return messages

        except PyMongoError as e:
            logger.error(f"Failed to get conversation for session {session_id}: {e}")
            return []

    async def vote_message(
        self,
        request: MessageVoteRequest,
        user_id: str,
    ) -> Optional[MessageDocument]:
        """Vote on a message"""
        try:
            update_data = {
                "upvote": request.upvote,
                "downvote": request.downvote,
                "feedback": request.feedback,
                "voted_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            result = self.collection.update_one(
                {"_id": request.message_id, "user_id": user_id, "is_active": True},
                {"$set": update_data},
            )

            if result.matched_count > 0:
                logger.info(f"Voted on message {request.message_id}")
                return await self.get_message(request.message_id, user_id)
            return None

        except PyMongoError as e:
            logger.error(f"Failed to vote on message {request.message_id}: {e}")
            return None

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[SessionSummary]:
        """Get user's sessions with message counts"""
        try:
            pipeline = [
                {"$match": {"user_id": user_id, "is_active": True}},
                {
                    "$group": {
                        "_id": "$session_id",
                        "user_id": {"$first": "$user_id"},
                        "title": {
                            "$first": "$title"
                        },  # Use stored title from first message
                        "message_count": {"$sum": 1},
                        "created_at": {"$min": "$created_at"},
                        "updated_at": {"$max": "$updated_at"},
                    }
                },
                {"$sort": {"updated_at": -1}},
                {"$skip": offset},
                {"$limit": limit},
            ]

            results = list(self.collection.aggregate(pipeline))
            sessions = []

            for result in results:
                session = SessionSummary(
                    session_id=result["_id"],
                    user_id=result["user_id"],
                    title=result.get("title"),  # Use title from database
                    message_count=result["message_count"],
                    created_at=datetime.fromisoformat(result["created_at"]),
                    updated_at=datetime.fromisoformat(result["updated_at"]),
                    is_active=True,
                )
                sessions.append(session)

            logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
            return sessions

        except PyMongoError as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            return []

    async def delete_message(self, message_id: str, user_id: str) -> bool:
        """Soft delete a message"""
        try:
            result = self.collection.update_one(
                {"_id": message_id, "user_id": user_id},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                },
            )
            success = result.matched_count > 0
            if success:
                logger.info(f"Deleted message {message_id}")
            return success
        except PyMongoError as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            return False

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Soft delete all messages in a session"""
        try:
            result = self.collection.update_many(
                {"session_id": session_id, "user_id": user_id},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                },
            )
            success = result.matched_count > 0
            if success:
                logger.info(
                    f"Deleted session {session_id} ({result.matched_count} messages)"
                )
            return success
        except PyMongoError as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    async def close(self):
        """Close the database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._collection = None
            logger.info("MongoDB connection closed")


def create_cosmos_service() -> CosmosService:
    """Factory function to create a CosmosService instance"""
    from app.core.config import settings
    from app.core.setup import _get_clients
    from app.services.title_service import create_title_service

    # Use MongoDB URL from config or default for testing
    mongodb_url = settings.MONGODB_URL or "mongodb://localhost:27017/"

    # Create title generation service
    title_service = None
    try:
        if not settings.USE_MOCK_CLIENTS:
            # Get production OpenAI client for title generation
            _, openai_client, _ = _get_clients()
            title_service = create_title_service(openai_client, model="gpt-35-turbo")
        else:
            # Get mock OpenAI client for testing
            from app.utils.mock_clients import get_mock_openai_client

            mock_client = get_mock_openai_client()
            title_service = create_title_service(mock_client, model="gpt-35-turbo")

        logger.info("Title generation service initialized successfully")
    except Exception as e:
        logger.warning(
            f"Failed to initialize title service: {e}, using simple fallback"
        )
        title_service = create_title_service()  # Creates SimpleTitleGenerationService

    return CosmosService(
        connection_string=mongodb_url,
        database_name=settings.cosmos_db_database_name,
        collection_name="messages",  # Single collection for all messages
        title_service=title_service,
    )
