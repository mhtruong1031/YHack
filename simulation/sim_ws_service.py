"""Async WebSocket server: Pi protocol (distance, sort) + harness pin I/O."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import websockets

from shared.protocol import (
    TYPE_DISTANCE,
    TYPE_ERROR,
    TYPE_EXECUTE_SORT,
    TYPE_GET_DISTANCE,
    TYPE_READY,
    TYPE_SORT_RESULT,
)

from . import config as sim_config
from .pin_protocol import (
    TYPE_GET_PIN_OUTPUTS,
    TYPE_PIN_INPUT,
    TYPE_PIN_OUTPUTS,
)
from .virtual_gpio import VirtualGPIO

logger = logging.getLogger(__name__)


async def run_sim_ws(virtual: VirtualGPIO, baseline_cm: float) -> None:
    async def handler(websocket) -> None:
        try:
            await websocket.send(
                json.dumps({"type": TYPE_READY, "calibrated_avg_cm": baseline_cm})
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
                    cm = await virtual.read_cm()
                    await websocket.send(json.dumps({"type": TYPE_DISTANCE, "cm": cm}))
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
                    await virtual.execute_sort(label, sim_config.SIM_MOTOR_HOLD_SEC)
                    cm = await virtual.read_cm()
                    await websocket.send(
                        json.dumps({"type": TYPE_SORT_RESULT, "cm": cm})
                    )
                except Exception as e:
                    logger.exception("execute_sort")
                    await websocket.send(
                        json.dumps({"type": TYPE_ERROR, "message": str(e)})
                    )
            elif msg_type == TYPE_PIN_INPUT:
                bcm = data.get("bcm")
                value = data.get("value")
                if not isinstance(bcm, int):
                    await websocket.send(
                        json.dumps(
                            {
                                "type": TYPE_ERROR,
                                "message": "pin_input requires int bcm",
                            }
                        )
                    )
                    continue
                if value is None or isinstance(value, bool) or not isinstance(
                    value, (int, float)
                ):
                    await websocket.send(
                        json.dumps(
                            {
                                "type": TYPE_ERROR,
                                "message": "pin_input requires numeric value",
                            }
                        )
                    )
                    continue
                try:
                    await virtual.set_pin_input(bcm, value)
                except Exception as e:
                    logger.exception("pin_input")
                    await websocket.send(
                        json.dumps({"type": TYPE_ERROR, "message": str(e)})
                    )
            elif msg_type == TYPE_GET_PIN_OUTPUTS:
                try:
                    outputs = await virtual.get_pin_outputs()
                    pins = {str(k): v for k, v in outputs.items()}
                    await websocket.send(
                        json.dumps({"type": TYPE_PIN_OUTPUTS, "pins": pins})
                    )
                except Exception as e:
                    logger.exception("get_pin_outputs")
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

    host = sim_config.SIM_WS_HOST
    port = sim_config.SIM_WS_PORT
    async with websockets.serve(handler, host, port):
        logger.info("Simulation WebSocket listening ws://%s:%s", host, port)
        await asyncio.Future()
