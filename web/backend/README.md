# Trash recycling social — FastAPI backend

Async FastAPI service with **PostgreSQL** (SQLAlchemy 2 + **psycopg** async), **Alembic** migrations (Supabase-compatible), Auth0 JWT validation (JWKS via HTTPX + `python-jose`), optional Google Gemini for drop valuation, and Plinko WebSocket push when exactly one user is connected.

## Prerequisites

- Python **3.11+**
- **PostgreSQL** (e.g. [Supabase](https://supabase.com) project) — connection URI in `DATABASE_URL`
- Auth0 application + API audience for JWTs
- Gemini API key for `/internal/drops` image valuation

## Setup

```bash
cd web/backend
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with real values (especially DATABASE_URL)
```

### Database migrations (Alembic)

From `web/backend` with `DATABASE_URL` set (same URI as in `.env`; Alembic rewrites it to **`postgresql+psycopg://`** for sync migrations via **psycopg** v3):

```bash
export DATABASE_URL="postgresql://postgres:...@...supabase.co:5432/postgres"
alembic upgrade head
```

Create new revisions after model changes:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Run

From **`web/backend`** only. If the repo root has its own `.venv` (`YHack/.venv`), activating that one leaves you **without** `uvicorn` / backend deps — use **this folder’s** venv (create it in the setup step above).

```bash
cd web/backend
source .venv/bin/activate   # must be web/backend/.venv, not the parent repo .venv
pip install -r requirements.txt   # once, into this venv
./.venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Using `./.venv/bin/python` avoids picking up another activated venv or a global `uvicorn` by mistake.

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
| `DATABASE_URL` | yes | Postgres URI (`postgresql://` or `postgres://`). The app upgrades it to **`postgresql+psycopg_async://`** at runtime (psycopg3). |
| `AUTH0_DOMAIN` | yes | Tenant host, e.g. `dev-xxx.us.auth0.com` |
| `AUTH0_AUDIENCE` | yes | API identifier / audience claim |
| `GEMINI_API_KEY` | yes | Google AI Studio / Gemini key |
| `DEVICE_INGEST_SECRET` | yes | Shared secret for `Authorization: Bearer <secret>` on `/internal/drops` |
| `CORS_ORIGINS` | no | Comma-separated origins; default `http://localhost:5173` |
| `GEMINI_MODEL` | no | Model id; default `gemini-1.5-flash` |

`main.py` calls `load_dotenv()` so a local `.env` is picked up for both Pydantic settings and CORS.

## Tables (PostgreSQL)

- **users** — `sub` (PK), `email`, `name`, `picture`, optional unique `handle`, `updated_at`
- **friend_edges** — `from_sub`, `to_sub`, `status` (`pending` \| `accepted`), `created_at`; unique pending direction via partial index
- **point_ledger** — `user_sub`, `points`, `source`, `drop_id`, `week_id`, `gemini_value`, `created_at`; idempotent award via unique `(user_sub, drop_id)`
- **drops** — `drop_id` (PK), `gemini_value`, optional `classification`, `image_base64` (JPEG, resized), `created_at`

Schema is managed with **Alembic** (`alembic/versions/`).

## Notable behaviors

- **`GET /api/me`** upserts the user from JWT claims and returns lifetime point total.
- **`POST /api/plinko/award`** is idempotent per `(user_sub, drop_id)`.
- **`POST /internal/drops`** resizes the image (max side 512px), calls Gemini for a single USD float, stores the drop, then pushes a WebSocket event **only** if exactly **one** distinct `sub` has active Plinko connections (avoids duplicate credit when multiple clients are connected).
