"""server/api_client.py contract vs web/backend FastAPI ingest (stub HTTP, no DB)."""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
import websockets

from tests.e2e.mock_pi import mock_pi_server


def _make_stub_server():
    records: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args) -> None:
            return

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            rec = {
                "path": self.path,
                "authorization": self.headers.get("Authorization", ""),
                "content_type": self.headers.get("Content-Type", ""),
                "body": body,
            }
            records.append(rec)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if self.path.rstrip("/") == "/internal/drops":
                self.wfile.write(
                    json.dumps(
                        {"drop_id": "stub-drop", "gemini_value": 0.25}
                    ).encode()
                )
            else:
                self.wfile.write(b"{}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"

    def shutdown() -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)

    return base, records, shutdown


def test_notify_drop_image_multipart_matches_backend_contract(
    monkeypatch: pytest.MonkeyPatch,
):
    import api_client
    import config as srv_config

    base, records, shutdown = _make_stub_server()
    try:
        secret = "device-shared-secret"
        monkeypatch.setenv("DROP_API_KEY", secret)
        monkeypatch.setattr(srv_config, "DROP_API_URL", f"{base}/internal/drops")
        monkeypatch.setattr(srv_config, "DROP_API_KEY_ENV", "DROP_API_KEY")

        jpeg = b"\xff\xd8\xff\xe0fake_jpeg_bytes"
        api_client.notify_drop_image(jpeg, "recyclable")

        assert len(records) == 1
        r = records[0]
        assert r["path"] == "/internal/drops"
        assert r["authorization"] == f"Bearer {secret}"
        assert "multipart/form-data" in r["content_type"]
        body = r["body"]
        assert b'name="image"' in body
        assert b"frame.jpg" in body
        assert b"image/jpeg" in body
        assert b'name="classification"' in body
        assert b"recyclable" in body
    finally:
        shutdown()


def test_notify_sort_result_json_post(monkeypatch: pytest.MonkeyPatch):
    import api_client
    import config as srv_config

    base, records, shutdown = _make_stub_server()
    try:
        secret = "sort-api-secret"
        monkeypatch.setenv("SORT_API_KEY", secret)
        monkeypatch.setattr(srv_config, "API_BASE_URL", f"{base}/api/sort-result")
        monkeypatch.setattr(srv_config, "API_KEY_ENV", "SORT_API_KEY")

        api_client.notify_sort_result("compost", {"device": "test"})

        assert len(records) == 1
        r = records[0]
        assert r["path"] == "/api/sort-result"
        assert r["authorization"] == f"Bearer {secret}"
        data = json.loads(r["body"].decode("utf-8"))
        assert data["classification"] == "compost"
        assert data["device"] == "test"
    finally:
        shutdown()


@pytest.mark.asyncio
async def test_orchestration_posts_drop_to_stub(
    fast_server_config, monkeypatch: pytest.MonkeyPatch
):
    base, records, shutdown = _make_stub_server()
    try:
        secret = "e2e-device-secret"
        monkeypatch.setenv("DROP_API_KEY", secret)
        import config as srv_config

        monkeypatch.setattr(srv_config, "DROP_API_URL", f"{base}/internal/drops")
        monkeypatch.setattr(srv_config, "DROP_API_KEY_ENV", "DROP_API_KEY")

        from server.main import run_with_pi

        async with mock_pi_server(calibrated_avg_cm=100.0) as (uri, state):
            n = {"i": 0}

            def distance_fn():
                if state.execute_sort_calls:
                    return 101.0
                n["i"] += 1
                if n["i"] <= 3:
                    return 100.0
                return 90.0

            state.set_distance_fn(distance_fn)

            stop = asyncio.Event()
            async with websockets.connect(uri) as ws:
                task = asyncio.create_task(run_with_pi(ws, run_stop_event=stop))
                for _ in range(300):
                    await asyncio.sleep(0.02)
                    if state.execute_sort_calls:
                        break
                assert state.execute_sort_calls

                for _ in range(200):
                    await asyncio.sleep(0.02)
                    if records:
                        break

                assert records, "expected POST /internal/drops from api_client"
                assert b'name="image"' in records[0]["body"]
                stop.set()
                await asyncio.wait_for(task, timeout=10.0)
    finally:
        shutdown()
