from __future__ import annotations

import time
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, Query

from . import db as db_module
from .models import ConversationOut, MessageCreate, MessageOut
from .ws import manager

router = APIRouter()


def _get_collection():
    collection = db_module.messages_collection
    if collection is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return collection


@router.get("/conversations", response_model=List[ConversationOut])
async def list_conversations() -> List[ConversationOut]:
    collection = _get_collection()

    pipeline = [
        {"$match": {"waId": {"$type": "string"}}},
        {"$sort": {"timestamps.whatsapp": 1, "_id": 1}},
        {
            "$group": {
                "_id": "$waId",
                "last": {"$last": "$$ROOT"},
                # Keep any non-empty name seen in the conversation
                "name": {"$max": {"$ifNull": ["$name", ""]}},
            }
        },
        {
            "$project": {
                "_id": 0,
                "waId": "$_id",
                "name": {"$cond": [{"$eq": ["$name", ""]}, None, "$name"]},
                "lastMessageText": "$last.text",
                "lastMessageAt": "$last.timestamps.whatsapp",
                "lastMessageDirection": "$last.direction",
                "lastMessageStatus": "$last.status",
            }
        },
        {"$sort": {"lastMessageAt": -1}},
    ]

    items: List[ConversationOut] = []
    async for row in collection.aggregate(pipeline):
        items.append(ConversationOut(**row))
    return items


@router.get("/messages", response_model=List[MessageOut])
async def list_messages(wa_id: str = Query(..., alias="wa_id")) -> List[MessageOut]:
    collection = _get_collection()
    cursor = collection.find({"waId": wa_id}).sort(
        [("timestamps.whatsapp", 1), ("_id", 1)]
    )
    docs = await cursor.to_list(length=None)
    return [MessageOut(**doc) for doc in docs]


@router.post("/messages", response_model=MessageOut, status_code=201)
async def create_message(payload: MessageCreate) -> MessageOut:
    collection = _get_collection()

    generated_id = f"local-{uuid.uuid4()}"
    now = int(time.time())

    doc = {
        "_id": generated_id,
        "waId": payload.waId,
        "name": None,
        "direction": "outbound",
        "text": payload.text,
        "type": "text",
        "status": "sent",
        "timestamps": {
            "whatsapp": now,
            "sent": now,
            "delivered": None,
            "read": None,
        },
        "businessPhone": None,
        "phoneNumberId": None,
        "conversationId": None,
        "gsId": None,
        "metaMsgId": None,
    }

    try:
        await collection.insert_one(doc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create message") from exc
    # Broadcast to WS subscribers
    await manager.broadcast({"type": "insert", "message": doc})
    return MessageOut(**doc)
