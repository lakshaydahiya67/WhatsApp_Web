from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


def get_env_optional(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


MONGODB_URI: str | None = get_env_optional("MONGODB_URI")
CORS_ORIGINS_RAW: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")


def parse_cors(origins_raw: str) -> List[str]:
    return [o.strip() for o in origins_raw.split(",") if o.strip()]


CORS_ORIGINS: List[str] = parse_cors(CORS_ORIGINS_RAW)
DATABASE_NAME: str = "whatsapp"
COLLECTION_MESSAGES: str = "processed_messages"
