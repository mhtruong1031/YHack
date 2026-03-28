# Trash recycling social — FastAPI backend

Async FastAPI service with MongoDB (Motor), Auth0 JWT validation (JWKS via HTTPX + `python-jose`), optional Google Gemini for drop valuation, and Plinko WebSocket push when exactly one user is connected.

## Prerequisites

- Python **3.11+**
- MongoDB reachable via `MONGODB_URI` (path should include the database name, e.g. `mongodb://localhost:27017/recycling`)
- Auth0 application + API audience for JWTs
- Gemini API key for `/internal/drops` image valuation

## Setup

```bash
cd web/backend
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with real values
```

## Run

```bash
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
python main.py
```

- API base: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Plinko WebSocket: `ws://localhost:8000/ws/plinko?token=<JWT>`

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | yes | Mongo connection string **with DB name in path** (recommended) |
| `AUTH0_DOMAIN` | yes | Tenant host, e.g. `dev-xxx.us.auth0.com` |
| `AUTH0_AUDIENCE` | yes | API identifier / audience claim |
| `GEMINI_API_KEY` | yes | Google AI Studio / Gemini key |
| `DEVICE_INGEST_SECRET` | yes | Shared secret for `Authorization: Bearer <secret>` on `/internal/drops` |
| `CORS_ORIGINS` | no | Comma-separated origins; default `http://localhost:5173` |
| `GEMINI_MODEL` | no | Model id; default `gemini-1.5-flash` |

`main.py` calls `load_dotenv()` so a local `.env` is picked up for both Pydantic settings and CORS.

## Collections (MongoDB)

- **users** — `sub` (primary key), `email`, `name`, `picture`, optional unique `handle`, `updated_at`
- **friend_edges** — `from_sub`, `to_sub`, `status` (`pending` \| `accepted`), `created_at`; unique pending direction via partial index
- **point_ledger** — `user_sub`, `points`, `source`, `drop_id`, `week_id` (e.g. `2026-W13`), `gemini_value`, `created_at`; idempotent award via unique `(user_sub, drop_id)`
- **drops** — `drop_id`, `gemini_value`, optional `classification`, `image_base64` (JPEG, resized), `created_at`

Indexes are created on application startup (`lifespan`).

## Notable behaviors

- **`GET /api/me`** upserts the user from JWT claims and returns lifetime point total.
- **`POST /api/plinko/award`** is idempotent per `(user_sub, drop_id)`.
- **`POST /internal/drops`** resizes the image (max side 512px), calls Gemini for a single USD float, stores the drop, then pushes a WebSocket event **only** if exactly **one** distinct `sub` has active Plinko connections (avoids duplicate credit when multiple clients are connected).
