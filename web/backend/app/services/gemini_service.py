import asyncio
import io
import json
import logging
import re
from typing import Any

import google.generativeai as genai
from PIL import Image

from app.config import Settings

logger = logging.getLogger(__name__)

_PROMPT = (
    "Return a single JSON object only. No markdown, no code fences, no other text.\n"
    'Schema: {"usd_value": <number>, "object_identity": <string>}\n'
    "- usd_value: estimated USD recyclable deposit value for the main object\n"
    '- object_identity: short debug label describing the main object (e.g. "plastic water bottle").\n'
)

def _extract_json_object(s: str) -> str | None:
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


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


def _response_text(response: Any) -> str:
    try:
        return (response.text or "").strip()
    except Exception:
        parts: list[str] = []
        for c in response.candidates or []:
            for p in c.content.parts or []:
                if hasattr(p, "text") and p.text:
                    parts.append(p.text)
        return "".join(parts).strip()


def _parse_json_estimate(text: str) -> tuple[float | None, str | None]:
    """
    Try to parse Gemini JSON. Returns (usd_value or None if missing, object_identity or None).
    """
    if not text:
        return None, None
    raw = text.strip()
    if raw.startswith("```"):
        fence_end = raw.rfind("```")
        if fence_end > 3:
            raw = raw[3:fence_end].strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].lstrip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        blob = _extract_json_object(text)
        if not blob:
            return None, None
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            return None, None

    if not isinstance(data, dict):
        return None, None

    usd: float | None = None
    if "usd_value" in data:
        try:
            usd = float(data["usd_value"])
        except (TypeError, ValueError):
            pass

    oid: str | None = None
    v = data.get("object_identity")
    if isinstance(v, str) and v.strip():
        oid = v.strip()
    elif v is not None:
        oid = str(v)

    return usd, oid


async def estimate_recyclable_value_usd(
    image_bytes: bytes,
    settings: Settings,
) -> tuple[float, dict[str, Any]]:
    """
    Returns (usd_value, gemini_debug). gemini_debug is for logging / API debug only;
    object_identity is not used for scoring or Plinko math.
    """
    gemini_debug: dict[str, Any] = {"object_identity": None}

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    try:
        response = await asyncio.to_thread(model.generate_content, [_PROMPT, img])
    except Exception as e:
        logger.exception("Gemini request failed: %s", e)
        gemini_debug["error"] = str(e)
        return 0.0, gemini_debug

    text = _response_text(response)
    gemini_debug["raw_text_preview"] = text[:500] if text else None

    usd_parsed, oid = _parse_json_estimate(text)
    gemini_debug["object_identity"] = oid

    if usd_parsed is not None:
        return float(usd_parsed), gemini_debug

    fallback = _parse_usd_float(text)
    gemini_debug["json_parse_failed"] = True
    logger.warning(
        "Gemini JSON parse failed; fallback numeric parse usd=%s preview=%r",
        fallback,
        text[:120],
    )
    return fallback, gemini_debug
