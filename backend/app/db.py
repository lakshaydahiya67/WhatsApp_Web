from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from .config import MONGODB_URI, DATABASE_NAME, COLLECTION_MESSAGES


mongo_client: AsyncIOMotorClient | None = None
messages_collection: AsyncIOMotorCollection | None = None


async def connect_to_mongo() -> None:
    global mongo_client, messages_collection
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set. Define it in .env before starting the server.")
    
    # MongoDB connection options for Atlas compatibility
    connection_options = {
        "tls": True,
        "tlsAllowInvalidCertificates": False,
        "retryWrites": True,
        "w": "majority",
        "serverSelectionTimeoutMS": 30000,
        "connectTimeoutMS": 30000,
        "socketTimeoutMS": 30000,
        "maxPoolSize": 10,
        "minPoolSize": 1
    }
    
    mongo_client = AsyncIOMotorClient(MONGODB_URI, **connection_options)
    db = mongo_client[DATABASE_NAME]
    messages_collection = db[COLLECTION_MESSAGES]
    
    # Test the connection
    try:
        await mongo_client.admin.command('ping')
        print("MongoDB connection successful!")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        raise
    
    # Indexes
    await messages_collection.create_index([("waId", 1), ("timestamps.whatsapp", -1)])


async def close_mongo_connection() -> None:
    global mongo_client
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
