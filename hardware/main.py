"""Raspberry Pi entrypoint: calibrate, then WebSocket server for motors + ultrasonic."""

import asyncio
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

import calibration
import config
import distance
import motors
from ws_service import run_hardware_ws

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main_async() -> None:
    logger.info(
        "Starting calibration (%.1f s, LED1 blinks)...",
        config.CALIBRATION_DURATION_SEC,
    )
    calibrated_avg_cm = calibration.run_calibration()
    logger.info("Calibrated average distance: %.2f cm", calibrated_avg_cm)
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
