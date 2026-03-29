import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware

from app.auth import decode_auth0_token_ws
from app.config import get_settings
from app.db import dispose_engine
from app.routers import friends, health, internal, leaderboard, me, plinko, users_search
from app.services.plinko_manager import plinko_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()


app = FastAPI(title="Trash Recycling Social API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
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


def _mount_spa_if_present(application: FastAPI) -> None:
    static_root = Path(__file__).resolve().parent / "static"
    index = static_root / "index.html"
    if not index.is_file():
        return
    assets = static_root / "assets"
    if assets.is_dir():
        application.mount("/assets", StaticFiles(directory=str(assets)), name="spa_assets")

    @application.get("/", include_in_schema=False)
    async def spa_index() -> FileResponse:
        return FileResponse(index)

    @application.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith(("api/", "internal/")):
            raise HTTPException(status_code=404)
        try:
            candidate = (static_root / full_path).resolve()
            static_resolved = static_root.resolve()
            candidate.relative_to(static_resolved)
        except ValueError:
            return FileResponse(index)
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


_mount_spa_if_present(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
