"""
Server-side configuration: WebSocket to Pi, CNN, camera, API, proximity tuning.
"""

import os

# --- WebSocket (Raspberry Pi hardware daemon) ---
WS_URL = (os.environ.get("WS_URL") or "ws://raspberrypi.local:8765").strip()

# --- Timing (mirror former hardware/main loop) ---
MAIN_LOOP_INTERVAL_SEC = 0.05
PROXIMITY_HOLD_SEC = 0.5
PROXIMITY_MARGIN_CM = 2.0
SORT_COOLDOWN_SEC = 2.0

# Repeat execute_sort on Pi while distance still below baseline - margin
MAX_SORT_RETRIES = 5

# --- Vision (PyTorch CNN) ---
CNN_MODEL_WEIGHTS_PATH = ""
CNN_IMAGE_SIZE = 224
CNN_CLASS_LABELS = ("waste", "recyclable", "compost")
CAMERA_DEVICE_INDEX = 0

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
