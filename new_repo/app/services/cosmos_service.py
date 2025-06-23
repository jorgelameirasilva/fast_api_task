"""Simplified MongoDB/CosmosDB service for chat sessions"""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.models.session import ChatSession, SessionSummary, SessionSearchRequest
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)


class CosmosService:
    """Simplified service for managing chat sessions in MongoDB/CosmosDB"""

    def __init__(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str = "sessions",
    ):
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
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
            self._collection.create_index([("user_id", 1), ("is_active", 1)])
            self._collection.create_index("updated_at")
            logger.info("Database indexes created successfully")
        except PyMongoError as e:
            logger.warning(f"Failed to create indexes: {e}")

    def _to_document(self, session: ChatSession) -> Dict[str, Any]:
        """Convert ChatSession to MongoDB document"""
        doc = session.model_dump()
        doc["_id"] = session.id
        doc["created_at"] = session.created_at.isoformat()
        doc["updated_at"] = session.updated_at.isoformat()
        doc["messages"] = [msg.model_dump() for msg in session.messages]
        return doc

    def _from_document(self, doc: Dict[str, Any]) -> ChatSession:
        """Convert MongoDB document to ChatSession"""
        doc["id"] = doc.pop("_id")
        doc["partition_key"] = doc["user_id"]  # Set partition_key same as user_id
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        doc["messages"] = [ChatMessage(**msg) for msg in doc.get("messages", [])]
        return ChatSession(**doc)

    def _to_summary(self, doc: Dict[str, Any]) -> SessionSummary:
        """Convert MongoDB document to SessionSummary"""
        return SessionSummary(
            id=doc["_id"],
            user_id=doc["user_id"],
            title=doc.get("title"),
            created_at=datetime.fromisoformat(doc["created_at"]),
            updated_at=datetime.fromisoformat(doc["updated_at"]),
            message_count=len(doc.get("messages", [])),
            is_active=doc.get("is_active", True),
        )

    def _generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate a session title from the first user message"""
        title = first_message.strip()
        if len(title) > max_length:
            title = title[: max_length - 3] + "..."
        return title

    def _trim_messages(
        self, messages: List[ChatMessage], max_messages: int
    ) -> List[ChatMessage]:
        """Trim messages keeping system messages and most recent others"""
        system_messages = [msg for msg in messages if msg.role == "system"]
        other_messages = [msg for msg in messages if msg.role != "system"]

        messages_to_keep = max_messages - len(system_messages)
        if messages_to_keep > 0:
            other_messages = other_messages[-messages_to_keep:]

        return system_messages + other_messages

    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        max_messages: int = 50,
    ) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            partition_key=user_id,  # Use user_id as partition key
            title=title,
            messages=[],
            context=context or {},
            max_messages=max_messages,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        try:
            document = self._to_document(session)
            self.collection.insert_one(document)
            logger.info(f"Created session {session.id} for user {user_id}")
            return session
        except PyMongoError as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def get_session(self, session_id: str, user_id: str) -> Optional[ChatSession]:
        """Get session by ID and user ID"""
        try:
            doc = self.collection.find_one({"_id": session_id, "user_id": user_id})
            if doc:
                return self._from_document(doc)
            return None
        except PyMongoError as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def update_session(self, session: ChatSession) -> ChatSession:
        """Update an existing session"""
        session.updated_at = datetime.utcnow()

        try:
            document = self._to_document(session)
            result = self.collection.replace_one(
                {"_id": session.id, "user_id": session.user_id}, document
            )

            if result.matched_count == 0:
                raise ValueError(f"Session {session.id} not found or access denied")

            logger.info(f"Updated session {session.id}")
            return session
        except PyMongoError as e:
            logger.error(f"Failed to update session {session.id}: {e}")
            raise

    async def add_message(
        self,
        session_id: str,
        user_id: str,
        message: ChatMessage,
        update_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ChatSession]:
        """Add a message to a session"""
        session = await self.get_session(session_id, user_id)
        if not session:
            return None

        # Add message
        session.messages.append(message)

        # Trim messages if needed
        if len(session.messages) > session.max_messages:
            session.messages = self._trim_messages(
                session.messages, session.max_messages
            )

        # Update context if provided
        if update_context:
            session.context.update(update_context)

        # Generate title if needed
        if not session.title and message.role == "user":
            session.title = self._generate_title(message.content)

        # Save changes
        return await self.update_session(session)

    async def list_sessions(
        self,
        user_id: str,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[SessionSummary]:
        """List sessions for a user"""
        try:
            query = {"user_id": user_id}
            if is_active is not None:
                query["is_active"] = is_active

            cursor = (
                self.collection.find(query, {"messages": 0})
                .sort("updated_at", -1)
                .skip(offset)
                .limit(limit)
            )

            return [self._to_summary(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            return []

    async def search_sessions(
        self, search_request: SessionSearchRequest
    ) -> List[SessionSummary]:
        """Search sessions based on criteria"""
        try:
            query = {"user_id": search_request.user_id}

            if search_request.is_active is not None:
                query["is_active"] = search_request.is_active

            if search_request.query:
                query["$or"] = [
                    {"title": {"$regex": search_request.query, "$options": "i"}},
                    {
                        "messages.content": {
                            "$regex": search_request.query,
                            "$options": "i",
                        }
                    },
                ]

            if search_request.start_date:
                query["created_at"] = {"$gte": search_request.start_date.isoformat()}

            if search_request.end_date:
                if "created_at" not in query:
                    query["created_at"] = {}
                query["created_at"]["$lte"] = search_request.end_date.isoformat()

            cursor = (
                self.collection.find(query, {"messages": 0})
                .sort("updated_at", -1)
                .limit(search_request.limit)
                .skip(search_request.offset)
            )

            return [self._to_summary(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Failed to search sessions: {e}")
            return []

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Soft delete a session"""
        try:
            result = self.collection.update_one(
                {"_id": session_id, "user_id": user_id},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                },
            )
            success = result.matched_count > 0
            if success:
                logger.info(f"Deleted session {session_id}")
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
    # Use MongoDB URL from environment or default for testing
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")

    return CosmosService(
        connection_string=mongodb_url,
        database_name=settings.cosmos_db_database_name,
        collection_name=settings.cosmos_db_container_name,
    )
