"""
Trash classification via Gemini + OpenCV camera on the server machine.

Lighting monitor: sustained shift in mean frame luminance vs an EWMA baseline
triggers the same classification path (see ``lighting_monitor_loop``).
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from typing import Literal, cast

import cv2
import numpy as np

import config
from shared.protocol import SORT_LABELS

Classification = Literal["waste", "recyclable", "compost"]

_cap: cv2.VideoCapture | None = None
_cap_lock = threading.Lock()
_genai_client = None  # lazy google.genai Client

DISPOSAL_TO_LABEL: dict[str, Classification] = {
    "waste": "waste",
    "compost": "compost",
    "recycle": "recyclable",
}

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "predicted_class": {"type": "string"},
        "disposal_category": {
            "type": "string",
            "enum": ["recycle", "compost", "waste"],
        },
        "estimated_value_usd": {"type": "number"},
    },
    "required": ["predicted_class", "disposal_category", "estimated_value_usd"],
}


def _open_capture() -> cv2.VideoCapture:
    idx = config.CAMERA_DEVICE_INDEX
    backend = (config.CAMERA_CAPTURE_BACKEND or "").strip()
    if backend.upper() == "V4L2":
        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    else:
        cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera at index {idx}")
    return cap


def _ensure_cap() -> cv2.VideoCapture:
    global _cap
    if _cap is None or not _cap.isOpened():
        _cap = _open_capture()
    return _cap


def release_camera() -> None:
    """Release the shared capture (e.g. on server shutdown)."""
    global _cap
    with _cap_lock:
        if _cap is not None:
            _cap.release()
            _cap = None


def get_frame() -> np.ndarray:
    """Capture one frame from the shared OpenCV device."""
    with _cap_lock:
        cap = _ensure_cap()
        ok, frame = cap.read()
    if not ok or frame is None:
        raise RuntimeError(
            f"Camera read failed (index {config.CAMERA_DEVICE_INDEX})"
        )
    return frame


def _blank_frame_jpeg() -> bytes:
    img = np.zeros((config.CNN_IMAGE_SIZE, config.CNN_IMAGE_SIZE, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    if not ok or buf is None:
        raise RuntimeError("JPEG encode failed for placeholder frame")
    return buf.tobytes()


def _gemini_api_key_set() -> bool:
    return bool((os.environ.get(config.GEMINI_API_KEY_ENV) or "").strip())


def _get_genai_client():
    global _genai_client
    if _genai_client is None:
        from google import genai

        key = (os.environ.get(config.GEMINI_API_KEY_ENV) or "").strip()
        if not key:
            raise RuntimeError(f"Set {config.GEMINI_API_KEY_ENV} for Gemini classification")
        _genai_client = genai.Client(api_key=key)
    return _genai_client


def run_gemini(frame_bgr: np.ndarray) -> Classification:
    from google.genai import types

    ok, buffer = cv2.imencode(".jpg", frame_bgr)
    if not ok or buffer is None:
        raise RuntimeError("Failed to encode frame as JPEG")

    prompt = (
        "You are classifying one trash item for a smart waste sorter. "
        "Return JSON only. "
        "Rules: "
        "1. predicted_class should be a short item name. "
        "2. disposal_category must be exactly one of: recycle, compost, waste. "
        "3. estimated_value_usd should be a numeric estimate of the recyclable refund or reuse value. "
        "   If the item has no meaningful recycling value, return 0.0. "
        "4. Assume this is a single item in an intake chamber."
    )

    client = _get_genai_client()
    response = client.models.generate_content(
        model=config.GEMINI_MODEL_NAME,
        contents=[
            prompt,
            types.Part.from_bytes(
                data=buffer.tobytes(),
                mime_type="image/jpeg",
            ),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
            temperature=0.1,
        ),
    )

    data = json.loads(response.text)
    cat = data.get("disposal_category", "waste")
    label = DISPOSAL_TO_LABEL.get(cat)
    if label is None:
        return cast(Classification, SORT_LABELS[0])
    return cast(Classification, label)


def analysis_with_frame(frame: np.ndarray | None = None) -> tuple[Classification, bytes]:
    """
    Classify from one BGR frame (or capture now), return (label, jpeg bytes).

    Without ``GEMINI_API_KEY`` (see config), returns a placeholder label and blank
    JPEG so orchestration can run headless.
    """
    if not _gemini_api_key_set():
        return cast(Classification, SORT_LABELS[0]), _blank_frame_jpeg()

    if frame is None:
        frame = get_frame()
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok or buf is None:
        raise RuntimeError("JPEG encode failed")
    jpeg_bytes = buf.tobytes()
    return run_gemini(frame), jpeg_bytes


def analysis() -> Classification:
    """Capture one view and classify trash type."""
    return analysis_with_frame()[0]


def lighting_monitor_loop(
    stop_event: threading.Event,
    loop: asyncio.AbstractEventLoop,
    trigger_queue: asyncio.Queue[str],
) -> None:
    """
    Poll the shared camera: when mean luminance stays away from the EWMA baseline
    by at least ``LIGHTING_DELTA_GRAY`` for ``LIGHTING_HOLD_SEC``, enqueue a trigger.

    This targets sustained illumination changes (shadows, lights, chamber door),
    not single-frame noise.
    """
    alpha = config.LIGHTING_EWMA_ALPHA
    delta_thr = config.LIGHTING_DELTA_GRAY
    hold_sec = config.LIGHTING_HOLD_SEC
    poll = config.LIGHTING_POLL_INTERVAL_SEC

    baseline: float | None = None
    deviation_since: float | None = None

    while not stop_event.is_set():
        try:
            with _cap_lock:
                cap = _ensure_cap()
                ok, frame = cap.read()
        except Exception:
            time.sleep(poll)
            continue

        if not ok or frame is None:
            time.sleep(poll)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_lux = float(np.mean(gray))
        now = time.time()

        if baseline is None:
            baseline = mean_lux
            time.sleep(poll)
            continue

        dev = abs(mean_lux - baseline)
        if dev < delta_thr:
            baseline = (1.0 - alpha) * baseline + alpha * mean_lux
            deviation_since = None
        else:
            if deviation_since is None:
                deviation_since = now
            elif now - deviation_since >= hold_sec:
                asyncio.run_coroutine_threadsafe(
                    trigger_queue.put("lighting"), loop
                )
                baseline = mean_lux
                deviation_since = None

        time.sleep(poll)

