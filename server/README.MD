# Server — laptop orchestrator (camera, Gemini, Pi WebSocket, API)

## Overview

Runs on a **computer** with a **USB (or built-in) camera**. It connects to the Raspberry Pi over **WebSocket** (`WS_URL`), receives the Pi `ready` message, then:

**Default (camera-only):** a background thread watches the **camera** for a sustained **lighting / luminance change**; when that fires, it captures a frame, runs **`analysis()`** (Gemini in [`analysis.py`](analysis.py)), sends **`execute_sort`** to the Pi, and posts results via [`api_client.py`](api_client.py) when configured.

**Optional Pi proximity:** set **`PROXIMITY_POLL=1`** to also poll **`get_distance`** on the Pi and trigger sorts when distance stays below `calibrated_avg_cm − PROXIMITY_MARGIN_CM` for **`PROXIMITY_HOLD_SEC`**. With proximity on, **`MAX_SORT_RETRIES`** can repeat **`execute_sort`** while Pi distance still reads “occupied.”

Protocol types live in [`../shared/protocol.py`](../shared/protocol.py).

## Configuration ([`config.py`](config.py))

| Setting | Purpose |
|---------|---------|
| `WS_URL` | e.g. `ws://raspberrypi.local:8765` |
| `PROXIMITY_POLL` | `1` = poll Pi distance for proximity; default **off** (camera trigger only) |
| `LIGHTING_TRIGGER` | `0` disables camera lighting trigger (use with `PROXIMITY_POLL=1` or nothing auto-triggers) |
| `MAIN_LOOP_INTERVAL_SEC`, `PROXIMITY_HOLD_SEC`, `PROXIMITY_MARGIN_CM`, `SORT_COOLDOWN_SEC` | Proximity loop timing (when `PROXIMITY_POLL=1`) |
| `MAX_SORT_RETRIES` | Repeated `execute_sort` while Pi distance deviated (when `PROXIMITY_POLL=1`) |
| `GEMINI_*`, `CAMERA_DEVICE_INDEX` | Vision and OpenCV device |
| `API_BASE_URL`, `API_KEY_ENV` | Optional HTTP POST after a cycle |
| `DROP_API_URL`, `DROP_API_KEY` | Optional multipart POST of frame JPEG; Bearer must match backend `DEVICE_INGEST_SECRET` (or set that var instead of `DROP_API_KEY`) |

## Setup

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

1. Start **`python main.py`** on the Pi from [`../hardware/`](../hardware/).
2. On the laptop:

```bash
cd server
source .venv/bin/activate
python main.py
```

Set `API_KEY` via the env name in `API_KEY_ENV` (default `SORT_API_KEY`) when using a protected API. For drop ingest, set `DROP_API_URL` (optional; defaults to production) and **`DROP_API_KEY`** or **`DEVICE_INGEST_SECRET`** (same value as Railway / `web/backend`).

## Layout

```
server/
  README.MD
  config.py
  main.py
  analysis.py
  CnnTrash.py
  api_client.py
  requirements.txt
```
