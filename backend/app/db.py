from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from .config import MONGODB_URI, DATABASE_NAME, COLLECTION_MESSAGES, COLLECTION_USERS


mongo_client: AsyncIOMotorClient | None = None
messages_collection: AsyncIOMotorCollection | None = None
users_collection: AsyncIOMotorCollection | None = None


async def connect_to_mongo() -> None:
    global mongo_client, messages_collection, users_collection
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set. Define it in .env before starting the server.")
    mongo_client = AsyncIOMotorClient(MONGODB_URI)
    db = mongo_client[DATABASE_NAME]
    messages_collection = db[COLLECTION_MESSAGES]
    users_collection = db[COLLECTION_USERS]
    # Indexes
    await messages_collection.create_index([("waId", 1), ("timestamps.whatsapp", -1)])
    # Users: unique username & optional email
    await users_collection.create_index("username", unique=True)
    await users_collection.create_index("email", unique=True, sparse=True)


async def close_mongo_connection() -> None:
    global mongo_client
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
