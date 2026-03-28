import asyncio
import io
import logging
import re

import google.generativeai as genai
from PIL import Image

from app.config import Settings

logger = logging.getLogger(__name__)

_PROMPT = (
    "Respond with only a number: the USD recyclable deposit value for the main "
    "object in this image. Use 0 if it is trash or not recyclable. No other text."
)


def _parse_usd_float(text: str) -> float:
    if not text:
        return 0.0
    cleaned = text.strip()
    for m in re.finditer(r"-?\d+(?:\.\d+)?", cleaned.replace(",", "")):
        try:
            return float(m.group())
        except ValueError:
            continue
    return 0.0


async def estimate_recyclable_value_usd(
    image_bytes: bytes,
    settings: Settings,
) -> float:
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    try:
        response = await asyncio.to_thread(model.generate_content, [_PROMPT, img])
    except Exception as e:
        logger.exception("Gemini request failed: %s", e)
        return 0.0
    text = ""
    try:
        text = response.text or ""
    except Exception:
        for c in response.candidates or []:
            for p in c.content.parts or []:
                if hasattr(p, "text") and p.text:
                    text += p.text
    return _parse_usd_float(text)
