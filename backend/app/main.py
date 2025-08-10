from __future__ import annotations

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import logging

from .config import CORS_ORIGINS
from .db import connect_to_mongo, close_mongo_connection
from .routes import router as api_router
from .ws import manager

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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger = logging.getLogger("uvicorn.access")
    path = request.url.path
    method = request.method
    try:
        response = await call_next(request)
        logger.info(f"{method} {path} -> {response.status_code}")
        return response
    except Exception as exc:
        logger.exception(f"Unhandled error on {method} {path}: {exc}")
        raise


app.include_router(api_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive; we don't process client messages for now
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        manager.disconnect(websocket)
