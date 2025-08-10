from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .db import connect_to_mongo, close_mongo_connection
from .routes import router as api_router

app = FastAPI(title="WhatsApp Web Clone API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    await connect_to_mongo()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await close_mongo_connection()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
