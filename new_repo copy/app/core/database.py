from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from loguru import logger
from .config import settings


class CosmosDatabase:
    def __init__(self):
        self._client: MongoClient = None
        self._database: Database = None

    def connect(self) -> None:
        """Connect to Cosmos DB"""
        try:
            if not settings.MONGODB_URL:
                logger.warning("MONGODB_URL not configured, using default connection")
                db_name = "chatdb"
                self._client = MongoClient("mongodb://localhost:27017/")
            else:
                self._client = MongoClient(settings.MONGODB_URL)
                # Use the database name from connection string or default
                db_name = (
                    settings.MONGODB_URL.split("/")[-1].split("?")[0]
                    if "/" in settings.MONGODB_URL
                    else "chatdb"
                )

            self._database = self._client[db_name]
            logger.info(f"Connected to Cosmos DB: {db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Cosmos DB: {e}")
            raise

    def get_collection(self, collection_name: str) -> Collection:
        """Get a collection from the database"""
        if not self._database:
            self.connect()
        return self._database[collection_name]

    def close(self) -> None:
        """Close database connection"""
        if self._client:
            self._client.close()
            logger.info("Closed Cosmos DB connection")


# Global database instance
cosmos_db = CosmosDatabase()


def get_sessions_collection() -> Collection:
    """Get the sessions collection"""
    return cosmos_db.get_collection("sessions")
