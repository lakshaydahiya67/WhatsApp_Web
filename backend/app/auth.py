from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from . import config
from .db import users_collection


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if not config.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set. Define it in .env before starting the server.")
    to_encode = {"sub": subject}
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    if not config.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set. Define it in .env before starting the server.")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        subject: str | None = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if users_collection is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    user = await users_collection.find_one({"_id": subject}) or await users_collection.find_one({"username": subject})
    if not user:
        raise credentials_exception
    if user.get("disabled"):
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
