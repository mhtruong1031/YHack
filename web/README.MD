# Trash Recycling Social (web)

React SPA + FastAPI backend: Auth0 login, friend graph, friend-scoped leaderboard (lifetime / weekly), Plinko fed by hardware drop ingest (Gemini USD estimate → WebSocket → Matter.js), macOS-style UI.

## Layout

- [`frontend/`](frontend/) — Vite + React + TypeScript (`npm run dev`, default `http://localhost:5173`)
- [`backend/`](backend/) — FastAPI (`uvicorn main:app --reload --port 8000`)

## Quick start

1. **PostgreSQL** (e.g. [Supabase](https://supabase.com)): copy **`DATABASE_URL`** from Project Settings → Database (URI). Run migrations from `backend/`: `alembic upgrade head`.
2. **Backend**: copy `backend/.env.example` → `backend/.env`, fill `DATABASE_URL`, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `GEMINI_API_KEY`, `DEVICE_INGEST_SECRET`. Run from `backend/` with venv + `pip install -r requirements.txt` + `uvicorn main:app --reload`.
3. **Auth0**: SPA app + API (audience). Allowed callback/logout URLs for dev (e.g. `http://localhost:5173`).
4. **Frontend**: copy `frontend/.env.example` → `frontend/.env`, set `VITE_AUTH0_*` and optionally `VITE_API_BASE_URL` (omit to use Vite proxy to `:8000`).
5. **Laptop server** ([`../server/`](../server/)): set `DROP_API_URL` (e.g. `http://localhost:8000/internal/drops`) and `DROP_API_KEY` to the same value as `DEVICE_INGEST_SECRET` so captured JPEGs hit the API after each sort cycle.

## Production: Vercel (frontend) + Railway (API)

Vite bakes **`VITE_*` into the JS at build time** — set them in the Vercel project **Environment Variables** (Production + Preview if you use previews), then **redeploy** after any change.

### Vercel (`web/frontend`)

| Variable | Example | Notes |
|----------|---------|--------|
| `VITE_AUTH0_DOMAIN` | `dev-xxx.us.auth0.com` | Same tenant as backend |
| `VITE_AUTH0_CLIENT_ID` | *(SPA application client id)* | Auth0 → Applications → SPA |
| `VITE_AUTH0_AUDIENCE` | `https://your-api-identifier` | **Must match** backend `AUTH0_AUDIENCE` if you use API access tokens |
| `VITE_API_BASE_URL` | `https://your-service.up.railway.app` | Public **HTTPS** Railway URL, **no trailing slash**. REST calls and Plinko **WSS** are derived from this. |

### Railway (API — recommend service root `web/backend`, not the repo-root Dockerfile)

Set **Variables** in the Railway service (same names as `backend/.env.example`):

| Variable | Required | Notes |
|----------|----------|--------|
| `DATABASE_URL` | yes | Supabase (or Postgres) URI; run **`alembic upgrade head`** once against this DB (CLI from `web/backend` or a one-off Railway command). |
| `AUTH0_DOMAIN` | yes | e.g. `dev-xxx.us.auth0.com` |
| `AUTH0_AUDIENCE` | yes | Same identifier as `VITE_AUTH0_AUDIENCE` |
| `GEMINI_API_KEY` | yes | For `/internal/drops` |
| `DEVICE_INGEST_SECRET` | yes | Same value you put in the laptop `DROP_API_KEY` |
| `CORS_ORIGINS` | **yes for Vercel** | Comma-separated list of **exact** browser origins, e.g. `https://your-app.vercel.app,https://www.yourdomain.com`. Must include every Vercel URL you use (production + previews are different URLs unless you use a single custom domain). |

`main.py` reads `CORS_ORIGINS` from the environment (defaults to `http://localhost:5173` only). If it’s wrong, the browser shows CORS errors on `/api/*`.

### Auth0 (SPA application)

Under **Applications → your SPA → Settings**, add to **Allowed Callback URLs**, **Allowed Logout URLs**, and **Allowed Web Origins**:

- `https://<your-vercel-app>.vercel.app`
- `http://localhost:5173` (keep for local dev)

Use **exact** URLs (scheme + host, no trailing slash unless Auth0 shows that pattern).

### Monolith alternative (no Vercel)

The repo **Dockerfile** builds the SPA with `VITE_API_BASE_URL` empty so the browser talks to the **same** Railway host for `/api` and `/ws/plinko`. Then you mainly need backend env vars on Railway; CORS is less critical for same-origin traffic.

## Demo flow

One user opens **Plinko** (WebSocket connects). When the bin triggers the laptop server, the backend runs Gemini and, if exactly one Plinko session is connected, pushes a `drop` event; the client spawns a ball and posts `/api/plinko/award` when the ball settles.
