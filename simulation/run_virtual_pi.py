"""Start the virtual Pi WebSocket daemon (same protocol surface as hardware/ws_service)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation.sim_ws_service import run_sim_ws
from simulation.virtual_gpio import VirtualGPIO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _async_main(baseline_cm: float) -> None:
    virtual = VirtualGPIO(baseline_cm=baseline_cm)
    await run_sim_ws(virtual, baseline_cm)


def main() -> None:
    parser = argparse.ArgumentParser(description="Virtual Pi WebSocket server")
    parser.add_argument(
        "--baseline-cm",
        type=float,
        default=None,
        help="Calibrated distance baseline (default: simulation.config.SIM_BASELINE_CM)",
    )
    args = parser.parse_args()

    from simulation import config as sim_config

    baseline = (
        float(args.baseline_cm)
        if args.baseline_cm is not None
        else float(sim_config.SIM_BASELINE_CM)
    )
    logger.info("Virtual Pi baseline_cm=%.2f", baseline)

    try:
        asyncio.run(_async_main(baseline))
    except KeyboardInterrupt:
        logger.info("Exiting.")


if __name__ == "__main__":
    main()
