from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field
from typing_extensions import Annotated
from pydantic import StringConstraints


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
    waId: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=20)]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ConversationOut(BaseModel):
    waId: Optional[str] = None
    name: Optional[str] = None
    lastMessageText: Optional[str] = None
    lastMessageAt: Optional[int] = None
    lastMessageDirection: Optional[Direction] = None
    lastMessageStatus: Status = None

    

# ===== Users / Auth =====

UsernameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)]
EmailStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=100)]
PasswordStr = Annotated[str, StringConstraints(min_length=6, max_length=128)]


class UserCreate(BaseModel):
    username: UsernameStr
    password: PasswordStr
    email: Optional[EmailStr] = None


class UserOut(BaseModel):
    id: str = Field(alias="_id")
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = False

    class Config:
        populate_by_name = True


class UserInDB(BaseModel):
    _id: str | None = None
    username: str
    email: Optional[str] = None
    hashed_password: str
    disabled: Optional[bool] = False
    created_at: Optional[int] = None


