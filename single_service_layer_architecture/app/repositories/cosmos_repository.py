"""
Cosmos DB Repository - Handles sessions and chat history with Azure Cosmos DB
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from loguru import logger

from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.cosmos.container import ContainerProxy
from azure.cosmos.database import DatabaseProxy


@dataclass
class CosmosMessage:
    """Cosmos DB message document"""
    
    id: str  # message_id
    content: str
    role: str  # "user" or "assistant"
    timestamp: str  # ISO format
    user_id: str
    session_id: str
    metadata: Optional[Dict] = None
    document_type: str = "message"  # For partitioning


@dataclass
class CosmosSession:
    """Cosmos DB session document"""
    
    id: str  # session_id
    user_id: str
    created_at: str  # ISO format
    updated_at: str  # ISO format
    context: Optional[Dict] = None
    title: Optional[str] = None
    message_count: int = 0
    document_type: str = "session"  # For partitioning


class CosmosRepository:
    """Repository for managing chat sessions and messages in Cosmos DB"""
    
    def __init__(self):
        """Initialize Cosmos DB connection"""
        self.endpoint = os.getenv("COSMOS_ENDPOINT")
        self.key = os.getenv("COSMOS_KEY") 
        self.database_name = os.getenv("COSMOS_DATABASE_NAME", "chatapp")
        self.container_name = os.getenv("COSMOS_CONTAINER_NAME", "chat_data")
        
        # Initialize client
        self.client: Optional[CosmosClient] = None
        self.database: Optional[DatabaseProxy] = None
        self.container: Optional[ContainerProxy] = None
        
        # Connection status
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Connect to Cosmos DB"""
        try:
            if not self.endpoint or not self.key:
                logger.warning("Cosmos DB credentials not provided, using mock mode")
                return False
                
            # Create client
            self.client = CosmosClient(self.endpoint, self.key)
            
            # Create database if it doesn't exist
            self.database = self.client.create_database_if_not_exists(
                id=self.database_name
            )
            
            # Create container if it doesn't exist
            # Using user_id as partition key for user isolation
            self.container = self.database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/user_id"),
                offer_throughput=400  # Minimum RU/s
            )
            
            self.is_connected = True
            logger.info("Successfully connected to Cosmos DB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Cosmos DB: {e}")
            self.is_connected = False
            return False
    
    # =============================================================================
    # SESSION OPERATIONS
    # =============================================================================
    
    async def create_session(self, session_id: str, user_id: str, 
                           context: Optional[Dict] = None, 
                           title: Optional[str] = None) -> bool:
        """Create a new chat session"""
        
        if not self.is_connected:
            logger.warning("Cosmos DB not connected, skipping session creation")
            return False
            
        try:
            now = datetime.utcnow().isoformat()
            
            session_doc = CosmosSession(
                id=session_id,
                user_id=user_id,
                created_at=now,
                updated_at=now,
                context=context or {},
                title=title,
                message_count=0
            )
            
            self.container.create_item(body=asdict(session_doc))
            logger.info(f"Created session {session_id} for user {user_id}")
            return True
            
        except exceptions.CosmosResourceExistsError:
            logger.warning(f"Session {session_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[CosmosSession]:
        """Get a session by ID"""
        
        if not self.is_connected:
            return None
            
        try:
            query = "SELECT * FROM c WHERE c.id = @session_id AND c.user_id = @user_id AND c.document_type = 'session'"
            parameters = [
                {"name": "@session_id", "value": session_id},
                {"name": "@user_id", "value": user_id}
            ]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id
            ))
            
            if items:
                item = items[0]
                return CosmosSession(**item)
            return None
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    async def update_session(self, session_id: str, user_id: str,
                           context: Optional[Dict] = None,
                           title: Optional[str] = None,
                           message_count: Optional[int] = None) -> bool:
        """Update session metadata"""
        
        if not self.is_connected:
            return False
            
        try:
            # Get existing session
            session = await self.get_session(session_id, user_id)
            if not session:
                return False
            
            # Update fields
            session.updated_at = datetime.utcnow().isoformat()
            if context is not None:
                session.context = context
            if title is not None:
                session.title = title
            if message_count is not None:
                session.message_count = message_count
            
            # Update in database
            self.container.replace_item(
                item=session_id,
                body=asdict(session)
            )
            
            logger.info(f"Updated session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[CosmosSession]:
        """Get all sessions for a user"""
        
        if not self.is_connected:
            return []
            
        try:
            query = """
                SELECT * FROM c 
                WHERE c.user_id = @user_id AND c.document_type = 'session'
                ORDER BY c.updated_at DESC
                OFFSET 0 LIMIT @limit
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit}
            ]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id
            ))
            
            return [CosmosSession(**item) for item in items]
            
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session and all its messages"""
        
        if not self.is_connected:
            return False
            
        try:
            # Delete all messages in the session
            await self.delete_session_messages(session_id, user_id)
            
            # Delete session document
            self.container.delete_item(
                item=session_id,
                partition_key=user_id
            )
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    # =============================================================================
    # MESSAGE OPERATIONS
    # =============================================================================
    
    async def save_message(self, message_id: str, content: str, role: str,
                          user_id: str, session_id: str, 
                          timestamp: Optional[datetime] = None,
                          metadata: Optional[Dict] = None) -> bool:
        """Save a chat message"""
        
        if not self.is_connected:
            return False
            
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            message_doc = CosmosMessage(
                id=message_id,
                content=content,
                role=role,
                timestamp=timestamp.isoformat(),
                user_id=user_id,
                session_id=session_id,
                metadata=metadata
            )
            
            self.container.create_item(body=asdict(message_doc))
            logger.debug(f"Saved message {message_id} to session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False
    
    async def get_session_messages(self, session_id: str, user_id: str,
                                  limit: Optional[int] = None) -> List[CosmosMessage]:
        """Get all messages for a session"""
        
        if not self.is_connected:
            return []
            
        try:
            if limit:
                query = """
                    SELECT * FROM c 
                    WHERE c.session_id = @session_id AND c.user_id = @user_id AND c.document_type = 'message'
                    ORDER BY c.timestamp DESC
                    OFFSET 0 LIMIT @limit
                """
                parameters = [
                    {"name": "@session_id", "value": session_id},
                    {"name": "@user_id", "value": user_id},
                    {"name": "@limit", "value": limit}
                ]
            else:
                query = """
                    SELECT * FROM c 
                    WHERE c.session_id = @session_id AND c.user_id = @user_id AND c.document_type = 'message'
                    ORDER BY c.timestamp ASC
                """
                parameters = [
                    {"name": "@session_id", "value": session_id},
                    {"name": "@user_id", "value": user_id}
                ]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id
            ))
            
            messages = [CosmosMessage(**item) for item in items]
            
            # If we got limited results, reverse to get chronological order
            if limit:
                messages.reverse()
                
            return messages
            
        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            return []
    
    async def delete_session_messages(self, session_id: str, user_id: str) -> bool:
        """Delete all messages for a session"""
        
        if not self.is_connected:
            return False
            
        try:
            # Get all message IDs for the session
            query = """
                SELECT c.id FROM c 
                WHERE c.session_id = @session_id AND c.user_id = @user_id AND c.document_type = 'message'
            """
            parameters = [
                {"name": "@session_id", "value": session_id},
                {"name": "@user_id", "value": user_id}
            ]
            
            message_ids = [item['id'] for item in self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id
            )]
            
            # Delete each message
            for message_id in message_ids:
                self.container.delete_item(
                    item=message_id,
                    partition_key=user_id
                )
            
            logger.info(f"Deleted {len(message_ids)} messages from session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session messages: {e}")
            return False
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    async def get_user_message_count(self, user_id: str) -> int:
        """Get total message count for a user"""
        
        if not self.is_connected:
            return 0
            
        try:
            query = """
                SELECT VALUE COUNT(1) FROM c 
                WHERE c.user_id = @user_id AND c.document_type = 'message'
            """
            parameters = [{"name": "@user_id", "value": user_id}]
            
            result = list(self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id
            ))
            
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"Error getting user message count: {e}")
            return 0
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Cleanup sessions older than specified days"""
        
        if not self.is_connected:
            return 0
            
        try:
            cutoff_date = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()
            
            # This would require a cross-partition query which is expensive
            # In production, consider using a scheduled job or TTL
            logger.warning("Session cleanup requires cross-partition query - implement as scheduled job")
            return 0
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0 