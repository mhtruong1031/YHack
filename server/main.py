"""Server orchestrator: WebSocket to Pi, proximity gate, Gemini vision, sort retries, API."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import threading
from pathlib import Path

# Keep package directory ahead of repo root so `import config` resolves to server/config.
_SERVER_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SERVER_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

import websockets

import analysis
import api_client
import config
from shared.protocol import (
    TYPE_DISTANCE,
    TYPE_ERROR,
    TYPE_EXECUTE_SORT,
    TYPE_GET_DISTANCE,
    TYPE_READY,
    TYPE_SORT_RESULT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _rpc(ws, payload: dict) -> dict:
    await ws.send(json.dumps(payload))
    raw = await ws.recv()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def _threshold_cm(calibrated_avg_cm: float) -> float:
    return calibrated_avg_cm - config.PROXIMITY_MARGIN_CM


def _still_deviated(cm: float, threshold_cm: float) -> bool:
    return cm < threshold_cm


def _run_hardware_sort_script_sync(label: str) -> None:
    """Run hardware/servo_test{3,4,5}.py for recyclable / waste / compost."""
    script = config.SERVO_SCRIPT_BY_LABEL.get(label)
    if script is None:
        logger.warning("no hardware servo script mapped for label %r", label)
        return
    if not script.is_file():
        logger.error("hardware sort script not found: %s", script)
        return
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(script.parent),
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()
        if len(tail) > 500:
            tail = tail[:500] + "..."
        logger.error(
            "hardware script %s exited %s: %s",
            script.name,
            proc.returncode,
            tail or "(no output)",
        )
    else:
        logger.info("hardware script finished: %s", script.name)


async def _run_hardware_sort_script(label: str) -> None:
    await asyncio.to_thread(_run_hardware_sort_script_sync, label)


async def _run_sort_cycle(
    ws: websockets.WebSocketClientProtocol,
    threshold_cm: float,
    reason: str,
) -> None:
    logger.info("%s; running analysis (Gemini)", reason)
    label, jpeg = await asyncio.to_thread(analysis.analysis_with_frame)

    for attempt in range(config.MAX_SORT_RETRIES):
        if config.HARDWARE_SORT_SCRIPTS_ENABLED:
            await _run_hardware_sort_script(label)
            sort_resp = await _rpc(ws, {"type": TYPE_GET_DISTANCE})
            if sort_resp.get("type") == TYPE_ERROR:
                logger.error(
                    "get_distance after hardware script: %s",
                    sort_resp.get("message"),
                )
                break
            if sort_resp.get("type") != TYPE_DISTANCE:
                logger.error("unexpected distance response: %s", sort_resp)
                break
            cm_after = float(sort_resp["cm"])
        else:
            sort_resp = await _rpc(
                ws,
                {"type": TYPE_EXECUTE_SORT, "label": label},
            )
            if sort_resp.get("type") == TYPE_ERROR:
                logger.error("execute_sort error: %s", sort_resp.get("message"))
                break
            if sort_resp.get("type") != TYPE_SORT_RESULT:
                logger.error("unexpected sort response: %s", sort_resp)
                break
            cm_after = float(sort_resp["cm"])
        logger.info(
            "sort_result attempt %s: distance %.2f cm",
            attempt + 1,
            cm_after,
        )
        if not _still_deviated(cm_after, threshold_cm):
            break
        if attempt + 1 < config.MAX_SORT_RETRIES:
            logger.info(
                "Still deviated vs threshold %.2f cm; repeating sort",
                threshold_cm,
            )

    api_client.notify_sort_result(label)
    api_client.notify_drop_image(jpeg, label)


async def _try_sort_cycle(
    ws: websockets.WebSocketClientProtocol,
    loop: asyncio.AbstractEventLoop,
    threshold_cm: float,
    reason: str,
    cooldown_until: list[float],
    sort_lock: asyncio.Lock,
) -> None:
    async with sort_lock:
        now = loop.time()
        if now < cooldown_until[0]:
            return
        await _run_sort_cycle(ws, threshold_cm, reason)
        cooldown_until[0] = loop.time() + config.SORT_COOLDOWN_SEC


async def _lighting_consumer(
    ws: websockets.WebSocketClientProtocol,
    loop: asyncio.AbstractEventLoop,
    threshold_cm: float,
    trigger_queue: asyncio.Queue[str],
    cooldown_until: list[float],
    sort_lock: asyncio.Lock,
) -> None:
    while True:
        await trigger_queue.get()
        await _try_sort_cycle(
            ws,
            loop,
            threshold_cm,
            "Sustained lighting change on camera",
            cooldown_until,
            sort_lock,
        )


async def run_with_pi(
    ws: websockets.WebSocketClientProtocol,
    run_stop_event: asyncio.Event | None = None,
) -> None:
    raw = await ws.recv()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    hello = json.loads(raw)
    if hello.get("type") != TYPE_READY:
        raise RuntimeError(f"expected {TYPE_READY}, got {hello!r}")
    baseline = float(hello["calibrated_avg_cm"])
    threshold_cm = _threshold_cm(baseline)
    logger.info(
        "Pi ready: baseline %.2f cm, proximity threshold %.2f cm",
        baseline,
        threshold_cm,
    )

    loop = asyncio.get_running_loop()
    below_since: float | None = None
    cooldown_until: list[float] = [0.0]
    sort_lock = asyncio.Lock()
    trigger_queue: asyncio.Queue[str] = asyncio.Queue()
    lighting_stop_flag = threading.Event()

    lighting_task: asyncio.Task[None] | None = None

    if config.LIGHTING_TRIGGER_ENABLED:
        threading.Thread(
            target=analysis.lighting_monitor_loop,
            args=(lighting_stop_flag, loop, trigger_queue),
            name="lighting-monitor",
            daemon=True,
        ).start()
        lighting_task = asyncio.create_task(
            _lighting_consumer(
                ws, loop, threshold_cm, trigger_queue, cooldown_until, sort_lock
            )
        )

    try:
        while True:
            await asyncio.sleep(config.MAIN_LOOP_INTERVAL_SEC)
            if run_stop_event is not None and run_stop_event.is_set():
                break
            now = loop.time()
            if now < cooldown_until[0]:
                below_since = None
                continue

            resp = await _rpc(ws, {"type": TYPE_GET_DISTANCE})
            if resp.get("type") == TYPE_ERROR:
                logger.warning("distance error: %s", resp.get("message"))
                below_since = None
                continue
            if resp.get("type") != TYPE_DISTANCE:
                logger.warning("unexpected message: %s", resp)
                below_since = None
                continue

            d = float(resp["cm"])

            if d < threshold_cm:
                if below_since is None:
                    below_since = now
                elif now - below_since >= config.PROXIMITY_HOLD_SEC:
                    await _try_sort_cycle(
                        ws,
                        loop,
                        threshold_cm,
                        "Proximity held",
                        cooldown_until,
                        sort_lock,
                    )
                    below_since = None
            else:
                below_since = None
    finally:
        lighting_stop_flag.set()
        if lighting_task is not None:
            lighting_task.cancel()
            try:
                await lighting_task
            except asyncio.CancelledError:
                pass
        analysis.release_camera()


async def main_async() -> None:
    uri = (config.WS_URL or "").strip()
    if not uri:
        raise SystemExit("Set config.WS_URL to ws://<pi-host>:<port>")

    logger.info("Connecting to Pi at %s", uri)
    async with websockets.connect(uri) as ws:
        await run_with_pi(ws)


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Exiting.")


if __name__ == "__main__":
    main()
