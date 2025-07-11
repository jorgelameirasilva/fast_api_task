#!/usr/bin/env python3
"""
Simple PyMongo setup script - just creates a sessions collection.
Keep it simple: one collection with embedded messages.
"""

import pymongo
import os
from datetime import datetime, timezone


def setup_simple_mongodb():
    """Create a simple database with just a sessions collection."""

    # Get connection string from environment or use default
    connection_string = os.getenv(
        "MONGODB_CONNECTION_STRING", "mongodb://localhost:27017"
    )
    print(f"Connecting to MongoDB: {connection_string}")

    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(connection_string)

        # Test connection
        client.admin.command("ping")
        print("✅ Successfully connected to MongoDB")

        # Create database
        db_name = "chat_app"
        db = client[db_name]
        print(f"✅ Created/accessed database: {db_name}")

        # Create simple sessions collection
        sessions_collection = db["sessions"]

        # Create indexes for better performance
        sessions_collection.create_index("user_id")
        sessions_collection.create_index("session_id", unique=True)
        sessions_collection.create_index("created_at")
        print(f"✅ Created collection: sessions with indexes")

        # Insert sample session with embedded messages (keep it simple!)
        sample_session = {
            "session_id": "sample_session_001",
            "user_id": "user_123",
            "title": "Sample Chat Session",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "messages": [
                {
                    "message_id": "msg_001",
                    "role": "user",
                    "content": "Hello, can you help me with something?",
                    "created_at": datetime.now(timezone.utc),
                },
                {
                    "message_id": "msg_002",
                    "role": "assistant",
                    "content": "Of course! I'd be happy to help. What do you need assistance with?",
                    "created_at": datetime.now(timezone.utc),
                    "sources": [],
                    "thoughts": "User is asking for help, providing a friendly response.",
                },
            ],
            "metadata": {"approach": "chatreadretrieveread", "overrides": {}},
        }

        try:
            sessions_collection.insert_one(sample_session)
            print(f"   📝 Inserted sample session with embedded messages")
        except pymongo.errors.DuplicateKeyError:
            print(f"   ℹ️  Sample session already exists")

        # Display database info
        print("\n📊 Database Summary:")
        print(f"Database: {db_name}")
        count = sessions_collection.count_documents({})
        print(f"  - sessions: {count} documents")

        print("\n🎉 Simple MongoDB setup completed successfully!")

        return db

    except Exception as e:
        print(f"❌ Error setting up MongoDB: {e}")
        raise
    finally:
        try:
            client.close()
        except:
            pass


def check_simple_mongodb():
    """Check the current status of the simple MongoDB setup."""

    connection_string = os.getenv(
        "MONGODB_CONNECTION_STRING", "mongodb://localhost:27017"
    )

    try:
        client = pymongo.MongoClient(connection_string)
        client.admin.command("ping")

        print("📊 MongoDB Status:")

        # List all databases
        databases = client.list_database_names()
        print(f"Databases: {databases}")

        # Check chat_app database
        if "chat_app" in databases:
            db = client["chat_app"]
            collections = db.list_collection_names()
            print(f"\nCollections in chat_app: {collections}")

            if "sessions" in collections:
                sessions = db["sessions"]
                count = sessions.count_documents({})
                print(f"Sessions collection: {count} documents")

                # Show a sample session
                sample = sessions.find_one({})
                if sample:
                    print(f"\nSample session structure:")
                    print(f'  - session_id: {sample.get("session_id")}')
                    print(f'  - user_id: {sample.get("user_id")}')
                    print(f'  - title: {sample.get("title")}')
                    print(f'  - messages: {len(sample.get("messages", []))} messages')
        else:
            print("chat_app database not found")

    except Exception as e:
        print(f"❌ Error checking MongoDB: {e}")
    finally:
        try:
            client.close()
        except:
            pass


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_simple_mongodb()
    else:
        setup_simple_mongodb()
