# Railway / single-host deploy: API + Vite SPA on one port (same origin for /api and /ws).
FROM node:20-alpine AS frontend-build
WORKDIR /app/web/frontend
COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci
COPY web/frontend/ ./
# Same origin as API — browser hits /api and wss://host/ws/plinko
ENV VITE_API_BASE_URL=
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY web/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY web/backend/ ./
COPY --from=frontend-build /app/web/frontend/dist ./static
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
