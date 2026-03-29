"""
Protocol-compatible mock Raspberry Pi WebSocket server (no GPIO).

Mirrors hardware/ws_service.py message shapes for CI and local dev.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import websockets

from shared.protocol import (
    SORT_LABELS,
    TYPE_DISTANCE,
    TYPE_ERROR,
    TYPE_EXECUTE_SORT,
    TYPE_GET_DISTANCE,
    TYPE_READY,
    TYPE_SORT_RESULT,
)

logger = logging.getLogger(__name__)


@dataclass
class MockPiState:
    """Mutable state shared with tests."""

    calibrated_avg_cm: float = 100.0
    execute_sort_calls: list[str] = field(default_factory=list)
    _distance_cm: float = 100.0
    _distance_fn: Callable[[], float] | None = None

    def distance_cm(self) -> float:
        if self._distance_fn is not None:
            return float(self._distance_fn())
        return float(self._distance_cm)

    def set_distance_cm(self, cm: float) -> None:
        self._distance_fn = None
        self._distance_cm = float(cm)

    def set_distance_fn(self, fn: Callable[[], float]) -> None:
        self._distance_fn = fn


def _handler_for_state(state: MockPiState):
    async def handler(websocket) -> None:
        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": TYPE_READY,
                        "calibrated_avg_cm": state.calibrated_avg_cm,
                    }
                )
            )
        except Exception as e:
            logger.error("mock pi: failed to send ready: %s", e)
            return

        async for message in websocket:
            if isinstance(message, bytes):
                message = message.decode("utf-8")
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send(
                    json.dumps({"type": TYPE_ERROR, "message": "invalid JSON"})
                )
                continue

            msg_type = data.get("type")
            if msg_type == TYPE_GET_DISTANCE:
                cm = state.distance_cm()
                await websocket.send(json.dumps({"type": TYPE_DISTANCE, "cm": cm}))
            elif msg_type == TYPE_EXECUTE_SORT:
                label = data.get("label")
                if not isinstance(label, str):
                    await websocket.send(
                        json.dumps({"type": TYPE_ERROR, "message": "missing label"})
                    )
                    continue
                if label not in SORT_LABELS:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": TYPE_ERROR,
                                "message": f"unknown label: {label!r}; expected one of {SORT_LABELS}",
                            }
                        )
                    )
                    continue
                state.execute_sort_calls.append(label)
                cm = state.distance_cm()
                await websocket.send(
                    json.dumps({"type": TYPE_SORT_RESULT, "cm": cm})
                )
            else:
                await websocket.send(
                    json.dumps(
                        {
                            "type": TYPE_ERROR,
                            "message": f"unknown type: {msg_type!r}",
                        }
                    )
                )

    return handler


@asynccontextmanager
async def mock_pi_server(
    *,
    calibrated_avg_cm: float = 100.0,
    host: str = "127.0.0.1",
    port: int = 0,
):
    """
    Start a mock Pi WebSocket server on an ephemeral port (if port=0).

    Yields (ws_uri, MockPiState).
    """
    state = MockPiState(calibrated_avg_cm=calibrated_avg_cm)
    handler = _handler_for_state(state)
    async with websockets.serve(handler, host, port) as server:
        sock = server.sockets[0]
        _, actual_port = sock.getsockname()[:2]
        uri = f"ws://{host}:{actual_port}"
        yield uri, state


async def _run_standalone() -> None:
    import os

    host = os.environ.get("MOCK_PI_HOST", "0.0.0.0")
    port = int(os.environ.get("MOCK_PI_PORT", "8765"))
    state = MockPiState(calibrated_avg_cm=100.0)
    handler = _handler_for_state(state)
    async with websockets.serve(handler, host, port):
        logger.info("mock Pi WebSocket ws://%s:%s (calibrated_avg_cm=%s)", host, port, state.calibrated_avg_cm)
        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run_standalone())
