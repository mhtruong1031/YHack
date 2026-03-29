#!/usr/bin/env python3
"""
POST a synthetic JPEG to POST /internal/drops (device ingest).

This matches what the laptop server sends via server/api_client.notify_drop_image.
If the FastAPI app is running and exactly one Plinko WebSocket client is connected,
the backend will push a ``drop`` event to that client.

Usage (from web/backend with venv + .env):

  # Local API
  uvicorn main:app --reload --port 8000
  python scripts/mock_plinko_drop.py

  # Production on Railway (secret must match Railway DEVICE_INGEST_SECRET)
  python scripts/mock_plinko_drop.py \\
      --url https://yhack-production.up.railway.app/internal/drops

  # Or set in .env: DROP_URL=https://yhack-production.up.railway.app/internal/drops
"""

from __future__ import annotations

import argparse
import os
import sys
from io import BytesIO
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

try:
    import httpx
    from dotenv import load_dotenv
    from PIL import Image
except ImportError:
    print("Install backend deps: pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1) from None


def _tiny_jpeg() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (64, 64), color=(90, 120, 80)).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def main() -> None:
    load_dotenv(_BACKEND_ROOT / ".env")

    p = argparse.ArgumentParser(description="Mock device drop → Plinko ingest")
    p.add_argument(
        "--url",
        default=os.environ.get("DROP_URL", "http://127.0.0.1:8000/internal/drops"),
        help="Full ingest URL (default: env DROP_URL or http://127.0.0.1:8000/internal/drops)",
    )
    p.add_argument(
        "--secret",
        default=os.environ.get("DEVICE_INGEST_SECRET", ""),
        help="Bearer token (default: env DEVICE_INGEST_SECRET)",
    )
    p.add_argument(
        "--classification",
        default="recyclable",
        help="Optional classification form field (default: recyclable)",
    )
    args = p.parse_args()

    if not args.secret.strip():
        print(
            "Missing secret: set DEVICE_INGEST_SECRET or pass --secret",
            file=sys.stderr,
        )
        raise SystemExit(2)

    jpeg = _tiny_jpeg()
    headers = {"Authorization": f"Bearer {args.secret.strip()}"}
    files = {"image": ("frame.jpg", jpeg, "image/jpeg")}
    data = {"classification": args.classification}

    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(args.url, files=files, data=data, headers=headers)
    except httpx.ConnectError as e:
        print(
            "Could not connect to the API (connection refused or unreachable).\n"
            f"  URL: {args.url}\n"
            "  Start the backend from web/backend, then retry:\n"
            "    uvicorn main:app --reload --port 8000\n"
            "  If the API runs elsewhere, pass --url https://host:port/internal/drops",
            file=sys.stderr,
        )
        raise SystemExit(1) from e
    except httpx.RequestError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        raise SystemExit(1) from e

    print(f"HTTP {r.status_code}")
    try:
        print(r.json())
    except Exception:
        print(r.text)
    if not r.is_success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
