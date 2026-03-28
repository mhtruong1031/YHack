import base64
import io
import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from PIL import Image

from app.config import Settings, get_settings
from app.db import get_database
from app.services.gemini_service import estimate_recyclable_value_usd
from app.services.plinko_manager import plinko_manager
from app.timeutil import utc_now

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["internal"])


def _device_auth(
    authorization: str | None = Header(None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )
    token = authorization[7:].strip()
    if token != settings.device_ingest_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device secret",
        )


def _resize_jpeg_max_side(data: bytes, max_side: int = 512, quality: int = 82) -> bytes:
    img = Image.open(io.BytesIO(data))
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


@router.post("/drops", dependencies=[Depends(_device_auth)])
async def ingest_drop(
    settings: Annotated[Settings, Depends(get_settings)],
    image: UploadFile = File(...),
    classification: str | None = Form(None),
) -> dict[str, Any]:
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty image")
    jpeg = _resize_jpeg_max_side(raw)
    gemini_value = await estimate_recyclable_value_usd(jpeg, settings)
    drop_id = str(uuid.uuid4())
    b64 = base64.b64encode(jpeg).decode("ascii")
    db = get_database()
    doc = {
        "drop_id": drop_id,
        "gemini_value": float(gemini_value),
        "classification": classification,
        "image_base64": b64,
        "created_at": utc_now(),
    }
    await db.drops.insert_one(doc)

    subs = plinko_manager.distinct_connected_subs()
    if len(subs) != 1:
        logger.info(
            "skip plinko ws push: expected exactly one connected sub, got %s (%s)",
            len(subs),
            subs,
        )
    else:
        only = next(iter(subs))
        payload = {
            "type": "drop",
            "drop_id": drop_id,
            "base_value_usd": float(gemini_value),
            "image_base64": f"data:image/jpeg;base64,{b64}",
        }
        await plinko_manager.broadcast_to_sub(only, payload)

    return {
        "drop_id": drop_id,
        "gemini_value": float(gemini_value),
        "classification": classification,
    }
