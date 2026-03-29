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

## Demo flow

One user opens **Plinko** (WebSocket connects). When the bin triggers the laptop server, the backend runs Gemini and, if exactly one Plinko session is connected, pushes a `drop` event; the client spawns a ball and posts `/api/plinko/award` when the ball settles.
