"""
Server-side configuration: WebSocket to Pi, Gemini vision, camera, API, proximity.
"""

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared.protocol import SORT_LABELS

# --- WebSocket (Raspberry Pi hardware daemon) ---
WS_URL = (os.environ.get("WS_URL") or "ws://raspberrypi.local:8765").strip()

# --- Timing (mirror former hardware/main loop) ---
MAIN_LOOP_INTERVAL_SEC = 0.05
PROXIMITY_HOLD_SEC = 0.5
PROXIMITY_MARGIN_CM = 2.0
SORT_COOLDOWN_SEC = 2.0

# Repeat execute_sort on Pi while distance still below baseline - margin
MAX_SORT_RETRIES = 5

# --- Vision (Gemini + OpenCV) ---
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-3-flash-preview")
# Placeholder JPEG size when API key unset (headless / tests)
CNN_IMAGE_SIZE = 224
CAMERA_DEVICE_INDEX = int(os.environ.get("CAMERA_DEVICE_INDEX", "0"))
# Empty = default backend; "V4L2" for Linux (see model/gemini_model.py)
CAMERA_CAPTURE_BACKEND = (os.environ.get("CAMERA_CAPTURE_BACKEND") or "").strip()

# Sustained mean-luminance change vs EWMA baseline (grayscale 0–255 scale)
LIGHTING_TRIGGER_ENABLED = os.environ.get("LIGHTING_TRIGGER", "1").lower() not in (
    "0",
    "false",
    "no",
)
LIGHTING_EWMA_ALPHA = float(os.environ.get("LIGHTING_EWMA_ALPHA", "0.06"))
LIGHTING_DELTA_GRAY = float(os.environ.get("LIGHTING_DELTA_GRAY", "12"))
LIGHTING_HOLD_SEC = float(os.environ.get("LIGHTING_HOLD_SEC", "0.6"))
LIGHTING_POLL_INTERVAL_SEC = float(os.environ.get("LIGHTING_POLL_INTERVAL_SEC", "0.04"))

# --- API ---
API_BASE_URL = ""
API_TIMEOUT_SEC = 10
API_KEY_ENV = "SORT_API_KEY"

# Drop / ingest: POST captured frame JPEG after a sort cycle. Empty URL skips.
# DROP_API_KEY_ENV names the env var for the Bearer token (same scheme as backend
# DEVICE_INGEST_SECRET). Set to "SORT_API_KEY" to reuse the sort API key.
DROP_API_URL = ""  # e.g. "http://localhost:8000/internal/drops"; empty = skip
DROP_API_KEY_ENV = "DROP_API_KEY"


def get_api_key() -> str | None:
    v = os.environ.get(API_KEY_ENV)
    return v if v else None


def get_drop_api_key() -> str | None:
    v = os.environ.get(DROP_API_KEY_ENV)
    return v if v else None
