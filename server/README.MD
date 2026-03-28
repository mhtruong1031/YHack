# Server — laptop orchestrator (CNN, proximity, API)

## Overview

Runs on a **computer** with a **USB (or built-in) camera**. It connects to the Raspberry Pi over **WebSocket** (`WS_URL`), receives the Pi’s calibrated distance baseline, then:

1. Polls **`get_distance`** on a short interval.
2. When distance stays below `calibrated_avg_cm − PROXIMITY_MARGIN_CM` for **`PROXIMITY_HOLD_SEC`**, captures a frame and runs **`analysis()`** (PyTorch `CnnTrash` in [`CnnTrash.py`](CnnTrash.py)).
3. Sends **`execute_sort`** with the predicted label. The Pi moves servos, resets, and returns **`sort_result`** with distance in cm.
4. If distance is still below the same threshold, repeats **`execute_sort`** (same label) up to **`MAX_SORT_RETRIES`**.
5. Calls **`notify_sort_result`** ([`api_client.py`](api_client.py)) if `API_BASE_URL` is set.
6. Calls **`notify_drop_image`** with the captured JPEG if `DROP_API_URL` is set.

Protocol types live in [`../shared/protocol.py`](../shared/protocol.py).

## Configuration ([`config.py`](config.py))

| Setting | Purpose |
|---------|---------|
| `WS_URL` | e.g. `ws://raspberrypi.local:8765` |
| `MAIN_LOOP_INTERVAL_SEC`, `PROXIMITY_HOLD_SEC`, `PROXIMITY_MARGIN_CM`, `SORT_COOLDOWN_SEC` | Same semantics as the original monolithic Pi loop |
| `MAX_SORT_RETRIES` | Cap on repeated sorts while still “deviated” |
| `CNN_*`, `CAMERA_DEVICE_INDEX` | Model and OpenCV device index |
| `API_BASE_URL`, `API_KEY_ENV` | Optional HTTP POST after a cycle |
| `DROP_API_URL`, `DROP_API_KEY_ENV` | Optional multipart POST of frame JPEG (`DROP_API_KEY` or reuse `SORT_API_KEY` via env var name) |

## Setup

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

PyTorch: use [pytorch.org](https://pytorch.org/get-started/locally/) if the default wheel does not match your OS/CPU/GPU.

## Run

1. Start **`python main.py`** on the Pi from [`../hardware/`](../hardware/).
2. On the laptop:

```bash
cd server
source .venv/bin/activate
python main.py
```

Set `API_KEY` via the env name in `API_KEY_ENV` (default `SORT_API_KEY`) when using a protected API. For drop ingest, set `DROP_API_URL` (empty to disable) and the secret in the env named by `DROP_API_KEY_ENV` (default `DROP_API_KEY`; set `DROP_API_KEY_ENV` to `SORT_API_KEY` to reuse the sort key).

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
