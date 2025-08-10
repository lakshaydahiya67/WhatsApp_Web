from __future__ import annotations

from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


Direction = Literal["inbound", "outbound"]
Status = Optional[Literal["sent", "delivered", "read"]]


class Timestamps(BaseModel):
    whatsapp: int
    sent: Optional[int] = None
    delivered: Optional[int] = None
    read: Optional[int] = None


class MessageOut(BaseModel):
    id: str = Field(alias="_id")
    waId: str
    name: Optional[str] = None
    direction: Direction
    text: Optional[str] = None
    type: Optional[str] = None
    status: Status = None
    timestamps: Timestamps
    businessPhone: Optional[str] = None
    phoneNumberId: Optional[str] = None
    conversationId: Optional[str] = None
    gsId: Optional[str] = None
    metaMsgId: Optional[str] = None

    class Config:
        populate_by_name = True


class MessageCreate(BaseModel):
    waId: str
    text: str


class ConversationOut(BaseModel):
    waId: Optional[str] = None
    name: Optional[str] = None
    lastMessageText: Optional[str] = None
    lastMessageAt: Optional[int] = None
    lastMessageDirection: Optional[Direction] = None
    lastMessageStatus: Status = None

    
