# Hardware ↔ Server ↔ Web: E2E tests and deployment

This document covers automated tests that simulate **Raspberry Pi hardware** + **laptop orchestrator** + **HTTP to the web backend**, and how to run the stack for real.

## Architecture

1. **Pi** (`hardware/`): WebSocket **server** on `0.0.0.0:8765` — **simulated** `get_distance` (configurable cm), `execute_sort`, no ultrasonic (see `shared/protocol.py`).
2. **Laptop server** (`server/`): WebSocket **client** to `WS_URL`, USB/built-in camera + Gemini classification, optional posts to the API.
3. **Web backend** (`web/backend/`): FastAPI — device ingest at `POST /internal/drops`, Plinko WebSocket, Auth0, Postgres.
4. **Web frontend** (`web/frontend/`): React SPA — `VITE_API_BASE_URL` points at the FastAPI app (not at `server/`).

The laptop server sends captured JPEGs to the backend with `notify_drop_image` (`server/api_client.py`), which matches `POST /internal/drops` in `web/backend/app/routers/internal.py`.

---

## Running E2E tests (CI / laptop, no Pi)

Tests live under `tests/e2e/`. They use a **mock Pi** WebSocket server (`tests/e2e/mock_pi.py`) and a **stub HTTP server** for `/internal/drops` contract checks — no GPIO, no Postgres.

### Setup

From the **repository root**:

```bash
python3 -m venv .venv-e2e
source .venv-e2e/bin/activate   # Windows: .venv-e2e\Scripts\activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` pulls in `pytest`, `pytest-asyncio`, and `server/requirements.txt` (including `websockets`, `requests`, OpenCV, etc.).

### Run

```bash
pytest tests/e2e -v
```

`pyproject.toml` sets `pythonpath = ["."]` and `asyncio_mode = auto`.

### What is covered

| Suite | Purpose |
|-------|---------|
| `test_protocol.py` | Mock Pi: `ready`, `get_distance`, `execute_sort` for each label, JSON/error paths |
| `test_orchestration_e2e.py` | Real `run_with_pi` against mock Pi: proximity hold → sort → `notify_*` hooks; `MAX_SORT_RETRIES` when distance stays low |
| `test_server_to_web_backend.py` | `api_client.notify_drop_image` / `notify_sort_result` against a local stub (multipart + Bearer); one test runs a full sort cycle and asserts a real POST to the stub |

**Note:** `tests/e2e/conftest.py` appends `server/` to `sys.path` so the same `import config` / `import analysis` resolution as `cd server && python main.py` applies inside tests.

### Manual mock Pi

To run the simulator alone (any machine):

```bash
python -m tests.e2e.mock_pi
```

Default: `ws://0.0.0.0:8765`. Override with `MOCK_PI_HOST` / `MOCK_PI_PORT`. Point `WS_URL` on the laptop at this address.

---

## Deployment: Pi + laptop server

### Raspberry Pi (hardware daemon)

- **Python 3.11+**, GPIO access (`gpio` group if needed).
- Install from `hardware/`:

  ```bash
  cd hardware
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  python main.py
  ```

- Listens on **`WS_HOST` / `WS_PORT`** in `hardware/config.py` (default `0.0.0.0:8765`).
- Ensure the laptop can reach the Pi (same LAN, firewall allows TCP **8765**). Use the Pi’s IP or hostname (e.g. `raspberrypi.local`).

### Laptop (orchestrator)

- From `server/` (or repo root with `PYTHONPATH` including `server` — see `server/main.py`):

  ```bash
  cd server
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  export WS_URL=ws://<pi-ip-or-hostname>:8765
  export GEMINI_API_KEY=...    # real classification; omit for placeholder-only
  ```

- **Camera-only (default):** sorts start when the **laptop camera** sees a sustained lighting change (`LIGHTING_TRIGGER` defaults on). **`PROXIMITY_POLL`** defaults **off** — the server does not use Pi `get_distance` to gate sorts. Set **`PROXIMITY_POLL=1`** if you want Pi distance polling again.
- **`LIGHTING_TRIGGER=0`:** only if you have no camera *and* you use **`PROXIMITY_POLL=1`**; otherwise nothing will trigger sorts.
- **`HARDWARE_SORT_SCRIPTS`**: leave unset or `0` for real split deployment so sorting runs on the Pi via **`execute_sort`**. If set to `1`, the server runs local `hardware/servo_test*.py` scripts (single-machine dev).

### Startup order

1. Start **Pi** (`hardware/main.py`).
2. Start **laptop server** (`server/main.py`).

### Troubleshooting

- **Cannot connect WebSocket**: wrong `WS_URL`, Pi not on network, firewall, or Pi not listening on `0.0.0.0`.
- **Wrong sort behavior**: confirm `HARDWARE_SORT_SCRIPTS=0` for Pi-driven sorting.

---

## Deployment: laptop server → web backend + frontend

Align env vars with `web/README.MD`.

### Backend (`web/backend/`)

- Postgres: `DATABASE_URL`, run `alembic upgrade head`.
- Auth0: `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`.
- `GEMINI_API_KEY` (used for `/internal/drops` valuation).
- **`DEVICE_INGEST_SECRET`**: Bearer secret for device ingest.

For a browser-hosted SPA on another origin, set **`CORS_ORIGINS`** to exact frontend origins (comma-separated).

### Laptop server → backend

- **`DROP_API_URL`**: if unset, the server defaults to `https://yhack-production.up.railway.app/internal/drops`. Set to a full URL to override, or set **`DROP_API_URL=`** (empty) to disable drop POSTs. Local example: `http://localhost:8000/internal/drops`.
- **`DROP_API_KEY`** (or the env name in `DROP_API_KEY_ENV`, default `DROP_API_KEY`): must equal **`DEVICE_INGEST_SECRET`** on the backend.

Optional JSON sort notification: set **`API_BASE_URL`** and **`SORT_API_KEY`** (env name `SORT_API_KEY` by default via `API_KEY_ENV`).

### Frontend (`web/frontend/`)

- Copy `frontend/.env.example` → `.env`.
- Set **`VITE_AUTH0_DOMAIN`**, **`VITE_AUTH0_CLIENT_ID`**, optional **`VITE_AUTH0_AUDIENCE`**.
- **`VITE_API_BASE_URL`**: public base URL of the FastAPI app (no trailing slash). REST and Plinko **WSS** are derived from this (see `src/lib/plinkoWs.ts`).

### Plinko / drop demo flow

When a physical sort completes, the laptop POSTs to `/internal/drops`. The backend may push a **`drop`** event over **`/ws/plinko`** only if **exactly one** distinct authenticated Plinko session is connected (see `web/backend/app/routers/internal.py`). For demos, keep a single Plinko tab open.

---

## Stack note

The laptop server uses **Gemini** + OpenCV for vision (`server/analysis.py`). Some older docs may still mention PyTorch/CNN; treat the code in `server/` as the source of truth.

## Browser E2E

Full Playwright/Cypress flows (Auth0 login + Plinko + live hardware) are optional. The automated suite here is **Python-only**; use manual checks for the SPA against your deployed API.
