#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Allow importing backend app config if needed
ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

try:
    from app.config import MONGODB_URI, DATABASE_NAME, COLLECTION_MESSAGES
except Exception:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.example")
    MONGODB_URI = os.environ.get("MONGODB_URI") or ""
    DATABASE_NAME = "whatsapp"
    COLLECTION_MESSAGES = "processed_messages"


STATUS_ORDER = {"sent": 1, "delivered": 2, "read": 3}


def promote_status(current: Optional[str], new: Optional[str]) -> Optional[str]:
    if new is None:
        return current
    if current is None:
        return new
    if STATUS_ORDER.get(new, 0) > STATUS_ORDER.get(current, 0):
        return new
    return current


@dataclass
class IngestStats:
    files_read: int = 0
    messages_upserted: int = 0
    statuses_applied: int = 0
    status_skipped_missing_message: int = 0


def find_value_block(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        entry = payload["metaData"]["entry"][0]
        change = entry["changes"][0]
        return change["value"]
    except Exception:
        return None


def is_message_payload(value: Dict[str, Any]) -> bool:
    return "messages" in value and isinstance(value.get("messages"), list)


def is_status_payload(value: Dict[str, Any]) -> bool:
    return "statuses" in value and isinstance(value.get("statuses"), list)


def extract_message_doc(value: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        msg = value["messages"][0]
        metadata = value.get("metadata", {})
        contacts = value.get("contacts", [])
        contact = contacts[0] if contacts else {}
        business_phone = metadata.get("display_phone_number")

        msg_id = msg.get("id")
        msg_from = msg.get("from")
        msg_type = msg.get("type")
        text = (msg.get("text") or {}).get("body")
        wa_id = None
        direction = None

        if business_phone and msg_from == business_phone:
            # outbound
            direction = "outbound"
            wa_id = contact.get("wa_id") or None
        else:
            # inbound
            direction = "inbound"
            wa_id = msg_from

        timestamps = {
            "whatsapp": int(msg.get("timestamp", 0) or 0),
            "sent": None,
            "delivered": None,
            "read": None,
        }

        status = "sent" if direction == "outbound" else "read"
        if direction == "inbound":
            timestamps["read"] = timestamps["whatsapp"]

        doc = {
            "_id": msg_id,
            "waId": wa_id,
            "name": (contact.get("profile") or {}).get("name"),
            "direction": direction,
            "text": text,
            "type": msg_type,
            "status": status,
            "timestamps": timestamps,
            "businessPhone": business_phone,
            "phoneNumberId": metadata.get("phone_number_id"),
            "conversationId": None,
            "gsId": None,
            "metaMsgId": None,
        }
        return doc
    except Exception:
        return None


def extract_status_updates(value: Dict[str, Any]) -> List[Dict[str, Any]]:
    updates: List[Dict[str, Any]] = []
    for st in value.get("statuses", []) or []:
        try:
            updates.append(
                {
                    "id": st.get("id"),
                    "meta_msg_id": st.get("meta_msg_id"),
                    "status": st.get("status"),
                    "timestamp": int(st.get("timestamp", 0) or 0),
                    "conversationId": (st.get("conversation") or {}).get("id"),
                    "gsId": st.get("gs_id"),
                    "recipient_id": st.get("recipient_id"),
                }
            )
        except Exception:
            continue
    return updates


async def upsert_message(collection, doc: Dict[str, Any]) -> bool:
    if not doc or not doc.get("_id"):
        return False
    await collection.update_one(
        {"_id": doc["_id"]},
        {
            "$setOnInsert": doc,
        },
        upsert=True,
    )
    return True


async def apply_status(collection, update: Dict[str, Any]) -> Optional[bool]:
    message_id = update.get("id") or update.get("meta_msg_id")
    if not message_id:
        return None

    # Fetch current to compute promotion and merge timestamps
    doc = await collection.find_one({"_id": message_id})
    if not doc:
        return False  # skip if message not present

    current_status = doc.get("status")
    new_status = promote_status(current_status, update.get("status"))
    timestamps = doc.get("timestamps") or {}

    ts_field = update.get("status")
    if ts_field in ("sent", "delivered", "read"):
        timestamps[ts_field] = update.get("timestamp")

    await collection.update_one(
        {"_id": message_id},
        {
            "$set": {
                "status": new_status,
                "timestamps": timestamps,
                "conversationId": update.get("conversationId") or doc.get("conversationId"),
                "gsId": update.get("gsId") or doc.get("gsId"),
                "metaMsgId": update.get("meta_msg_id") or doc.get("metaMsgId"),
            }
        },
    )
    return True


async def ingest_directory(dir_path: Path) -> IngestStats:
    stats = IngestStats()

    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set. Define it in .env before running ingestion.")

    client = AsyncIOMotorClient(MONGODB_URI)
    collection = client[DATABASE_NAME][COLLECTION_MESSAGES]

    json_files = sorted([p for p in dir_path.glob("*.json")])
    for file_path in json_files:
        stats.files_read += 1
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            continue

        value = find_value_block(payload)
        if not value:
            continue

        if is_message_payload(value):
            doc = extract_message_doc(value)
            if doc and await upsert_message(collection, doc):
                stats.messages_upserted += 1

        if is_status_payload(value):
            for upd in extract_status_updates(value):
                res = await apply_status(collection, upd)
                if res is True:
                    stats.statuses_applied += 1
                elif res is False:
                    stats.status_skipped_missing_message += 1

    client.close()
    return stats


async def main() -> None:
    # Default directory with spaces matches provided folder name
    default_dir = ROOT / "whatsapp sample payloads"
    dir_str = os.environ.get("INGEST_DIR", str(default_dir))
    dir_path = Path(dir_str)

    if not dir_path.exists():
        raise FileNotFoundError(f"Payload directory not found: {dir_path}")

    stats = await ingest_directory(dir_path)
    print(
        json.dumps(
            {
                "files_read": stats.files_read,
                "messages_upserted": stats.messages_upserted,
                "statuses_applied": stats.statuses_applied,
                "status_skipped_missing_message": stats.status_skipped_missing_message,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
