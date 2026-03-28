"""Server orchestrator: WebSocket to Pi, proximity gate, CNN, sort retries, API."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
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


async def run_with_pi(ws: websockets.WebSocketClientProtocol) -> None:
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
    cooldown_until = 0.0

    while True:
        await asyncio.sleep(config.MAIN_LOOP_INTERVAL_SEC)
        now = loop.time()
        if now < cooldown_until:
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
                logger.info("Proximity held; running analysis (CNN)")
                label, jpeg = await asyncio.to_thread(analysis.analysis_with_frame)

                for attempt in range(config.MAX_SORT_RETRIES):
                    sort_resp = await _rpc(
                        ws,
                        {"type": TYPE_EXECUTE_SORT, "label": label},
                    )
                    if sort_resp.get("type") == TYPE_ERROR:
                        logger.error(
                            "execute_sort error: %s", sort_resp.get("message")
                        )
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
                cooldown_until = now + config.SORT_COOLDOWN_SEC
                below_since = None
        else:
            below_since = None


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
