"""Async WebSocket server: simulated distance reads and execute_sort on the Pi."""

import asyncio
import json
import logging
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

import websockets

from shared.protocol import (
    TYPE_DISTANCE,
    TYPE_ERROR,
    TYPE_EXECUTE_SORT,
    TYPE_GET_DISTANCE,
    TYPE_READY,
    TYPE_SORT_RESULT,
)

import config
import distance
import motors

logger = logging.getLogger(__name__)


async def run_hardware_ws(calibrated_avg_cm: float) -> None:
    distance.init_sensor()
    motors.init_motors()

    async def handler(websocket):
        try:
            await websocket.send(
                json.dumps(
                    {"type": TYPE_READY, "calibrated_avg_cm": calibrated_avg_cm}
                )
            )
        except Exception as e:
            logger.error("failed to send ready: %s", e)
            return

        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send(
                    json.dumps({"type": TYPE_ERROR, "message": "invalid JSON"})
                )
                continue

            msg_type = data.get("type")
            if msg_type == TYPE_GET_DISTANCE:
                try:
                    cm = distance.read_cm()
                    await websocket.send(
                        json.dumps({"type": TYPE_DISTANCE, "cm": cm})
                    )
                except Exception as e:
                    logger.exception("get_distance")
                    await websocket.send(
                        json.dumps({"type": TYPE_ERROR, "message": str(e)})
                    )
            elif msg_type == TYPE_EXECUTE_SORT:
                label = data.get("label")
                if not isinstance(label, str):
                    await websocket.send(
                        json.dumps({"type": TYPE_ERROR, "message": "missing label"})
                    )
                    continue
                try:
                    motors.execute_sort(label)
                    cm = distance.read_cm()
                    await websocket.send(
                        json.dumps({"type": TYPE_SORT_RESULT, "cm": cm})
                    )
                except Exception as e:
                    logger.exception("execute_sort")
                    await websocket.send(
                        json.dumps({"type": TYPE_ERROR, "message": str(e)})
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

    async with websockets.serve(handler, config.WS_HOST, config.WS_PORT):
        logger.info(
            "WebSocket server listening ws://%s:%s",
            config.WS_HOST,
            config.WS_PORT,
        )
        await asyncio.Future()
