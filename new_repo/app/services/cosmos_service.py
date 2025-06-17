"""Cosmos DB service for session management"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from azure.cosmos.aio import CosmosClient, DatabaseProxy, ContainerProxy
from azure.cosmos import exceptions

from app.core.config import settings
from app.models.session import ChatSession, SessionSummary, SessionSearchRequest
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)


class CosmosSessionService:
    """Service for managing chat sessions in Cosmos DB"""

    def __init__(self):
        self.client: Optional[CosmosClient] = None
        self.database: Optional[DatabaseProxy] = None
        self.container: Optional[ContainerProxy] = None
        self._initialized = False

    async def initialize(self):
        """Initialize Cosmos DB client and ensure database/container exist"""
        if self._initialized:
            return

        try:
            if not settings.cosmos_db_endpoint or not settings.cosmos_db_key:
                logger.warning("Cosmos DB credentials not configured, using mock mode")
                self._initialized = True
                return

            # Initialize client
            self.client = CosmosClient(
                url=settings.cosmos_db_endpoint, credential=settings.cosmos_db_key
            )

            # Create database if it doesn't exist
            database_name = settings.cosmos_db_database_name
            try:
                self.database = await self.client.create_database_if_not_exists(
                    id=database_name
                )
                logger.info(f"Database '{database_name}' ready")
            except Exception as e:
                logger.error(f"Failed to create/access database: {e}")
                raise

            # Create container if it doesn't exist
            container_name = settings.cosmos_db_container_name
            try:
                self.container = await self.database.create_container_if_not_exists(
                    id=container_name,
                    partition_key={
                        "kind": "Hash",
                        "paths": [settings.cosmos_db_partition_key],
                    },
                    offer_throughput=400,  # RU/s for shared throughput
                )
                logger.info(f"Container '{container_name}' ready")
            except Exception as e:
                logger.error(f"Failed to create/access container: {e}")
                raise

            self._initialized = True
            logger.info("Cosmos DB service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Cosmos DB service: {e}")
            raise

    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        max_messages: int = 50,
    ) -> ChatSession:
        """Create a new chat session"""
        await self.initialize()

        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        session = ChatSession(
            id=session_id,
            user_id=user_id,
            partition_key=user_id,
            title=title,
            context=context or {},
            max_messages=max_messages,
            created_at=now,
            updated_at=now,
            messages=[],
            is_active=True,
        )

        if self.container:
            try:
                await self.container.create_item(
                    body=session.model_dump(), partition_key=user_id
                )
                logger.info(f"Created session {session_id} for user {user_id}")
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Failed to create session: {e}")
                raise

        return session

    async def get_session(self, session_id: str, user_id: str) -> Optional[ChatSession]:
        """Retrieve a specific session"""
        await self.initialize()

        if not self.container:
            logger.warning("Cosmos DB not available, returning None")
            return None

        try:
            response = await self.container.read_item(
                item=session_id, partition_key=user_id
            )
            return ChatSession(**response)
        except exceptions.CosmosResourceNotFoundError:
            logger.info(f"Session {session_id} not found for user {user_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve session {session_id}: {e}")
            raise

    async def update_session(self, session: ChatSession) -> ChatSession:
        """Update an existing session"""
        await self.initialize()

        session.updated_at = datetime.utcnow()

        if self.container:
            try:
                await self.container.replace_item(
                    item=session.id,
                    body=session.model_dump(),
                    partition_key=session.user_id,
                )
                logger.debug(f"Updated session {session.id}")
            except Exception as e:
                logger.error(f"Failed to update session {session.id}: {e}")
                raise

        return session

    async def add_message_to_session(
        self,
        session_id: str,
        user_id: str,
        message: ChatMessage,
        update_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ChatSession]:
        """Add a message to a session and update context"""
        session = await self.get_session(session_id, user_id)
        if not session:
            return None

        # Add message to conversation history
        session.messages.append(message)

        # Trim messages if over limit
        if len(session.messages) > session.max_messages:
            # Keep system messages and trim user/assistant pairs
            system_messages = [msg for msg in session.messages if msg.role == "system"]
            other_messages = [msg for msg in session.messages if msg.role != "system"]

            # Keep the most recent messages
            messages_to_keep = session.max_messages - len(system_messages)
            if messages_to_keep > 0:
                other_messages = other_messages[-messages_to_keep:]

            session.messages = system_messages + other_messages

        # Update context if provided
        if update_context:
            session.context.update(update_context)

        # Auto-generate title if not set and this is the first user message
        if not session.title and message.role == "user":
            session.title = self._generate_session_title(message.content)

        return await self.update_session(session)

    async def list_user_sessions(
        self,
        user_id: str,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[SessionSummary]:
        """List sessions for a user with pagination"""
        await self.initialize()

        if not self.container:
            logger.warning("Cosmos DB not available, returning empty list")
            return []

        # Build query
        query = "SELECT * FROM c WHERE c.user_id = @user_id"
        parameters = [{"name": "@user_id", "value": user_id}]

        if is_active is not None:
            query += " AND c.is_active = @is_active"
            parameters.append({"name": "@is_active", "value": is_active})

        query += " ORDER BY c.updated_at DESC"
        query += f" OFFSET {offset} LIMIT {limit}"

        try:
            items = []
            async for item in self.container.query_items(
                query=query, parameters=parameters, partition_key=user_id
            ):
                session_summary = SessionSummary(
                    id=item["id"],
                    user_id=item["user_id"],
                    title=item.get("title"),
                    created_at=datetime.fromisoformat(
                        item["created_at"].replace("Z", "+00:00")
                    ),
                    updated_at=datetime.fromisoformat(
                        item["updated_at"].replace("Z", "+00:00")
                    ),
                    message_count=len(item.get("messages", [])),
                    is_active=item.get("is_active", True),
                )
                items.append(session_summary)

            return items

        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            raise

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session (or mark as inactive)"""
        await self.initialize()

        session = await self.get_session(session_id, user_id)
        if not session:
            return False

        # Mark as inactive instead of deleting for data retention
        session.is_active = False
        await self.update_session(session)

        logger.info(f"Marked session {session_id} as inactive")
        return True

    async def search_sessions(
        self, search_request: SessionSearchRequest
    ) -> List[SessionSummary]:
        """Search sessions with advanced filtering"""
        await self.initialize()

        if not self.container:
            logger.warning("Cosmos DB not available, returning empty list")
            return []

        # Build dynamic query
        query_parts = ["SELECT * FROM c WHERE 1=1"]
        parameters = []

        if search_request.user_id:
            query_parts.append("AND c.user_id = @user_id")
            parameters.append({"name": "@user_id", "value": search_request.user_id})

        if search_request.is_active is not None:
            query_parts.append("AND c.is_active = @is_active")
            parameters.append({"name": "@is_active", "value": search_request.is_active})

        if search_request.created_after:
            query_parts.append("AND c.created_at >= @created_after")
            parameters.append(
                {
                    "name": "@created_after",
                    "value": search_request.created_after.isoformat(),
                }
            )

        if search_request.created_before:
            query_parts.append("AND c.created_at <= @created_before")
            parameters.append(
                {
                    "name": "@created_before",
                    "value": search_request.created_before.isoformat(),
                }
            )

        query_parts.append("ORDER BY c.updated_at DESC")
        query_parts.append(
            f"OFFSET {search_request.offset} LIMIT {search_request.limit}"
        )

        query = " ".join(query_parts)

        try:
            items = []
            async for item in self.container.query_items(
                query=query, parameters=parameters, enable_cross_partition_query=True
            ):
                session_summary = SessionSummary(
                    id=item["id"],
                    user_id=item["user_id"],
                    title=item.get("title"),
                    created_at=datetime.fromisoformat(
                        item["created_at"].replace("Z", "+00:00")
                    ),
                    updated_at=datetime.fromisoformat(
                        item["updated_at"].replace("Z", "+00:00")
                    ),
                    message_count=len(item.get("messages", [])),
                    is_active=item.get("is_active", True),
                )
                items.append(session_summary)

            return items

        except Exception as e:
            logger.error(f"Failed to search sessions: {e}")
            raise

    def _generate_session_title(self, first_message: str) -> str:
        """Generate a session title from the first user message"""
        # Keep first 50 characters and add ellipsis if longer
        title = first_message.strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title

    async def close(self):
        """Close the Cosmos DB client connection"""
        if self.client:
            await self.client.close()
            logger.info("Cosmos DB client closed")


# Global service instance
cosmos_session_service = CosmosSessionService()
