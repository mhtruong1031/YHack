import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware

from app.auth import decode_auth0_token_ws
from app.config import get_settings
from app.db import get_client, init_indexes
from app.routers import friends, health, internal, leaderboard, me, plinko, users_search
from app.services.plinko_manager import plinko_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_indexes()
    yield
    client = get_client()
    client.close()


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(title="Trash Recycling Social API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(me.router)
app.include_router(leaderboard.router)
app.include_router(users_search.router)
app.include_router(friends.router)
app.include_router(plinko.router)
app.include_router(internal.router)


@app.websocket("/ws/plinko")
async def ws_plinko(websocket: WebSocket, token: str) -> None:
    settings = get_settings()
    try:
        claims = await decode_auth0_token_ws(token, settings)
    except Exception as e:
        logger.debug("ws jwt failed: %s", e)
        await websocket.close(code=4401)
        return
    sub = claims["sub"]
    await websocket.accept()
    plinko_manager.register(sub, websocket)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=45.0)
                if msg.strip().lower() == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        plinko_manager.unregister(sub, websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
