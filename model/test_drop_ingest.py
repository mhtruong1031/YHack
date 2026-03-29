"""
Exercise the same drop ingest path as server/api_client.notify_drop_image:

  POST multipart to DROP_API_URL (e.g. http://localhost:8000/internal/drops)
  with field ``image`` (JPEG) and optional ``classification``,
  Bearer DROP_API_KEY matching the backend ``device_ingest_secret``.

If a browser has Plinko open with exactly one WS session, the backend may push
``type: "drop"`` after this request succeeds.

Usage:
  export DROP_API_URL=http://localhost:8000/internal/drops
  export DROP_API_KEY=<same as DEVICE_INGEST_SECRET on the API>
  python model/test_drop_ingest.py
  python model/test_drop_ingest.py --classification recyclable
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys

try:
    import requests
except ImportError as e:
    print("Need requests (see server/requirements.txt):", e, file=sys.stderr)
    sys.exit(1)

# Tiny valid JPEG (no OpenCV) so this runs in a minimal venv.
_MINI_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
    "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCA"
    "ABAAEDAREAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgED"
    "AwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGR"
    "olJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKT"
    "lJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP"
    "09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBA"
    "QAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpK"
    "jU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJma"
    "oqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9o"
    "ADAMBAAIRAxEAPwD3+iiigD//2Q=="
)


def _synthetic_jpeg_bytes() -> bytes:
    """Small valid JPEG (no camera, no OpenCV)."""
    return base64.b64decode(_MINI_JPEG_B64)


def main() -> int:
    p = argparse.ArgumentParser(description="POST a test JPEG to internal drop ingest.")
    p.add_argument(
        "--classification",
        default=os.environ.get("DROP_TEST_CLASSIFICATION", "test_item"),
        help="Form field sent with the image (default: test_item or DROP_TEST_CLASSIFICATION).",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("DROP_TEST_TIMEOUT", "60")),
        help="HTTP timeout seconds (Gemini on the API can be slow).",
    )
    args = p.parse_args()

    url = (os.environ.get("DROP_API_URL") or "").strip()
    if not url:
        print(
            "DROP_API_URL is not set. Example:\n"
            "  export DROP_API_URL=http://localhost:8000/internal/drops",
            file=sys.stderr,
        )
        return 1

    key = (os.environ.get("DROP_API_KEY") or "").strip()
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    else:
        print(
            "Warning: DROP_API_KEY unset; backend will return 401 if auth is required.",
            file=sys.stderr,
        )

    jpeg = _synthetic_jpeg_bytes()
    files = {"image": ("test_frame.jpg", jpeg, "image/jpeg")}
    data = {}
    if args.classification:
        data["classification"] = args.classification

    try:
        r = requests.post(url, files=files, data=data, headers=headers, timeout=args.timeout)
    except requests.RequestException as e:
        print("Request failed:", e, file=sys.stderr)
        return 1

    print("HTTP", r.status_code)
    try:
        body = r.json()
        print(json.dumps(body, indent=2))
    except json.JSONDecodeError:
        print(r.text[:2000])

    if not r.ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
