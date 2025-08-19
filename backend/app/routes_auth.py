from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel

from .auth import create_access_token, get_current_user, get_password_hash, verify_password
from .db import users_collection
from .models import UserCreate, UserOut


router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _get_users_collection():
    if users_collection is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return users_collection


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserCreate) -> UserOut:
    col = _get_users_collection()
    # Check duplicates
    existing = await col.find_one({"username": payload.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user_doc = {
        "_id": str(uuid.uuid4()),
        "username": payload.username,
        "email": payload.email,
        "hashed_password": get_password_hash(payload.password),
        "created_at": int(time.time()),
        "disabled": False,
    }
    try:
        await col.insert_one(user_doc)
    except Exception as exc:
        # For unique email collisions, etc.
        raise HTTPException(status_code=400, detail="Registration failed") from exc
    return UserOut(**user_doc)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest = Body(...)) -> TokenResponse:
    col = _get_users_collection()
    user = await col.find_one({"username": payload.username})
    if not user or not verify_password(payload.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user["_id"])  # subject = user id
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: dict[str, Any] = Depends(get_current_user)) -> UserOut:
    # current_user is a raw Mongo document
    return UserOut(**current_user)
