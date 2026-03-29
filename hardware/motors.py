"""Servo-based sort motions: simultaneous holds, then reset to home (0°)."""

import logging
import time

from gpiozero import AngularServo

import config
from shared.protocol import SORT_LABELS

logger = logging.getLogger(__name__)

_servos: tuple[AngularServo, AngularServo, AngularServo] | None = None


def _make_servo(pin: int) -> AngularServo:
    return AngularServo(
        pin,
        min_angle=config.SERVO_MIN_ANGLE,
        max_angle=config.SERVO_MAX_ANGLE,
    )


def init_motors() -> None:
    global _servos
    if _servos is not None:
        return
    _servos = (
        _make_servo(config.SERVO_MOTOR_A_PIN),
        _make_servo(config.SERVO_MOTOR_B_PIN),
        _make_servo(config.SERVO_MOTOR_C_PIN),
    )
    reset_all()


def close_motors() -> None:
    global _servos
    if _servos is None:
        return
    for s in _servos:
        s.close()
    _servos = None


def reset_all() -> None:
    """Return A, B, C to home (0°)."""
    if _servos is None:
        return
    for s in _servos:
        s.angle = 0
    time.sleep(0.3)


def execute_sort(label: str) -> None:
    """
    Run class-specific motion (simultaneous where multiple motors), hold MOTOR_HOLD_SEC,
    then reset all servos to home.
    """
    if _servos is None:
        raise RuntimeError("motors not initialized")
    a, b, c = _servos
    hold = config.MOTOR_HOLD_SEC

    reset_all()

    if label not in SORT_LABELS:
        raise ValueError(f"unknown label: {label!r}; expected one of {SORT_LABELS}")

    if label == "waste":
        a.angle = config.ANGLE_WASTE_A
        b.angle = config.ANGLE_WASTE_B
        c.angle = 0
        logger.info("sort motion: waste (A=%s B=%s) hold %.1fs", config.ANGLE_WASTE_A, config.ANGLE_WASTE_B, hold)
    elif label == "recyclable":
        a.angle = 0
        b.angle = config.ANGLE_RECYCLABLE_B
        c.angle = 0
        logger.info("sort motion: recyclable (B=%s) hold %.1fs", config.ANGLE_RECYCLABLE_B, hold)
    elif label == "compost":
        a.angle = 0
        b.angle = config.ANGLE_COMPOST_B
        c.angle = config.ANGLE_COMPOST_C
        logger.info(
            "sort motion: compost (B=%s C=%s) hold %.1fs",
            config.ANGLE_COMPOST_B,
            config.ANGLE_COMPOST_C,
            hold,
        )
    time.sleep(hold)
    reset_all()
