"""In-process virtual ultrasonic + servos + LED for the simulation WebSocket server."""

from __future__ import annotations

import asyncio
import logging

from . import config as sim_config

logger = logging.getLogger(__name__)


class VirtualGPIO:
    """Thread-safe async state: distance (echo pin), servo angles, LED."""

    def __init__(self, baseline_cm: float | None = None) -> None:
        self._lock = asyncio.Lock()
        base = float(baseline_cm if baseline_cm is not None else sim_config.SIM_BASELINE_CM)
        self.distance_cm: float = base
        self._servo_angle: dict[int, float] = {
            sim_config.SERVO_MOTOR_A_PIN: 0.0,
            sim_config.SERVO_MOTOR_B_PIN: 0.0,
            sim_config.SERVO_MOTOR_C_PIN: 0.0,
        }
        self._led: int = 0

    def read_cm_sync(self) -> float:
        """Sync read of cached distance (no lock — use only from locked sections or tests)."""
        return self.distance_cm

    async def read_cm(self) -> float:
        async with self._lock:
            return self.distance_cm

    async def set_pin_input(self, bcm: int, value: float | int) -> None:
        async with self._lock:
            if bcm == sim_config.ULTRASONIC_ECHO_PIN:
                self.distance_cm = float(value)
            elif bcm == sim_config.LED1_PIN:
                self._led = int(value)
            else:
                logger.debug("set_pin_input ignored unknown bcm=%s value=%s", bcm, value)

    async def get_pin_outputs(self) -> dict[int, float | int]:
        async with self._lock:
            out: dict[int, float | int] = {
                sim_config.SERVO_MOTOR_A_PIN: self._servo_angle[sim_config.SERVO_MOTOR_A_PIN],
                sim_config.SERVO_MOTOR_B_PIN: self._servo_angle[sim_config.SERVO_MOTOR_B_PIN],
                sim_config.SERVO_MOTOR_C_PIN: self._servo_angle[sim_config.SERVO_MOTOR_C_PIN],
                sim_config.LED1_PIN: self._led,
            }
            return dict(out)

    async def _reset_servos(self) -> None:
        for p in self._servo_angle:
            self._servo_angle[p] = 0.0
        await asyncio.sleep(sim_config.SIM_RESET_SLEEP_SEC)

    async def execute_sort(self, label: str, hold_sec: float) -> None:
        """
        Match hardware/motors.execute_sort: reset, pose, hold, reset.
        Uses SIM_RESET_SLEEP_SEC instead of motors.reset_all 0.3s.
        """
        async with self._lock:
            await self._reset_servos()

            if label == "waste":
                self._servo_angle[sim_config.SERVO_MOTOR_A_PIN] = float(sim_config.ANGLE_WASTE_A)
                self._servo_angle[sim_config.SERVO_MOTOR_B_PIN] = float(sim_config.ANGLE_WASTE_B)
                self._servo_angle[sim_config.SERVO_MOTOR_C_PIN] = 0.0
                logger.info(
                    "virtual sort: waste (A=%s B=%s) hold %.2fs",
                    sim_config.ANGLE_WASTE_A,
                    sim_config.ANGLE_WASTE_B,
                    hold_sec,
                )
            elif label == "recyclable":
                self._servo_angle[sim_config.SERVO_MOTOR_A_PIN] = 0.0
                self._servo_angle[sim_config.SERVO_MOTOR_B_PIN] = float(sim_config.ANGLE_RECYCLABLE_B)
                self._servo_angle[sim_config.SERVO_MOTOR_C_PIN] = 0.0
                logger.info(
                    "virtual sort: recyclable (B=%s) hold %.2fs",
                    sim_config.ANGLE_RECYCLABLE_B,
                    hold_sec,
                )
            elif label == "compost":
                self._servo_angle[sim_config.SERVO_MOTOR_A_PIN] = 0.0
                self._servo_angle[sim_config.SERVO_MOTOR_B_PIN] = float(sim_config.ANGLE_COMPOST_B)
                self._servo_angle[sim_config.SERVO_MOTOR_C_PIN] = float(sim_config.ANGLE_COMPOST_C)
                logger.info(
                    "virtual sort: compost (B=%s C=%s) hold %.2fs",
                    sim_config.ANGLE_COMPOST_B,
                    sim_config.ANGLE_COMPOST_C,
                    hold_sec,
                )
            else:
                raise ValueError(f"unknown label: {label!r}")

        # Release lock during hold so other clients can poll get_pin_outputs / read_cm.
        await asyncio.sleep(hold_sec)
        async with self._lock:
            await self._reset_servos()
