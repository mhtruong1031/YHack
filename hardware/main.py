"""Raspberry Pi entrypoint: WebSocket server for motors + simulated distance."""

import asyncio
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

import config
import distance
import motors
from ws_service import run_hardware_ws

from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16, address=0x40)

# Center all
kit.servo[0].angle = 0
kit.servo[1].angle = 180
kit.servo[2].angle = 90
time.sleep(2)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main_async() -> None:
    calibrated_avg_cm = float(config.SIMULATED_CALIBRATED_AVG_CM)
    logger.info(
        "Using simulated distance (%.2f cm baseline, read_cm=%.2f cm); starting WebSocket…",
        calibrated_avg_cm,
        config.SIMULATED_DISTANCE_CM,
    )
    await run_hardware_ws(calibrated_avg_cm)


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Exiting.")
    finally:
        motors.close_motors()
        distance.close_sensor()


if __name__ == "__main__":
    main()
