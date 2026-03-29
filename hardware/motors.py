"""Servo-based sort motions: simultaneous holds, then reset to home."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import config
from shared.protocol import SORT_LABELS

if TYPE_CHECKING:
    from gpiozero import AngularServo

logger = logging.getLogger(__name__)

_servos_gpio: tuple[Any, Any, Any] | None = None
_kit: Any | None = None


def _kit_angle(gpiozero_style_deg: float) -> float:
    """Map config angles (-90..90, 0 = center) to ServoKit 0..180."""
    return max(0.0, min(180.0, 90.0 + float(gpiozero_style_deg)))


def _make_servo(pin: int) -> AngularServo:
    from gpiozero import AngularServo as _AngularServo

    return _AngularServo(
        pin,
        min_angle=config.SERVO_MIN_ANGLE,
        max_angle=config.SERVO_MAX_ANGLE,
    )


def init_motors() -> None:
    global _servos_gpio, _kit
    if config.SERVO_BACKEND == "servokit":
        if _kit is not None:
            return
        try:
            from adafruit_servokit import ServoKit
        except ImportError as e:
            raise RuntimeError(
                "SERVO_BACKEND=servokit requires adafruit-circuitpython-servokit "
                "(pip install -r requirements.txt)"
            ) from e
        _kit = ServoKit(
            channels=config.SERVOKIT_NUM_CHANNELS,
            address=config.SERVOKIT_I2C_ADDRESS,
        )
        logger.info(
            "motors: backend=servokit address=0x%x channels A=%s B=%s C=%s",
            config.SERVOKIT_I2C_ADDRESS,
            config.SERVOKIT_CHANNEL_A,
            config.SERVOKIT_CHANNEL_B,
            config.SERVOKIT_CHANNEL_C,
        )
        reset_all()
        return

    if _servos_gpio is not None:
        return
    _servos_gpio = (
        _make_servo(config.SERVO_MOTOR_A_PIN),
        _make_servo(config.SERVO_MOTOR_B_PIN),
        _make_servo(config.SERVO_MOTOR_C_PIN),
    )
    logger.info(
        "motors: backend=gpiozero pins A=%s B=%s C=%s",
        config.SERVO_MOTOR_A_PIN,
        config.SERVO_MOTOR_B_PIN,
        config.SERVO_MOTOR_C_PIN,
    )
    reset_all()


def close_motors() -> None:
    global _servos_gpio, _kit
    if _servos_gpio is not None:
        for s in _servos_gpio:
            s.close()
        _servos_gpio = None
    _kit = None


def reset_all() -> None:
    """Return A, B, C to home (0° in config convention → 90° on ServoKit)."""
    if config.SERVO_BACKEND == "servokit" and _kit is not None:
        for ch in (
            config.SERVOKIT_CHANNEL_A,
            config.SERVOKIT_CHANNEL_B,
            config.SERVOKIT_CHANNEL_C,
        ):
            _kit.servo[ch].angle = _kit_angle(0)
        time.sleep(0.3)
        return
    if _servos_gpio is None:
        return
    for s in _servos_gpio:
        s.angle = 0
    time.sleep(0.3)


def _apply_angles(a: float, b: float, c: float) -> None:
    if config.SERVO_BACKEND == "servokit" and _kit is not None:
        _kit.servo[config.SERVOKIT_CHANNEL_A].angle = _kit_angle(a)
        _kit.servo[config.SERVOKIT_CHANNEL_B].angle = _kit_angle(b)
        _kit.servo[config.SERVOKIT_CHANNEL_C].angle = _kit_angle(c)
        return
    if _servos_gpio is None:
        return
    ga, gb, gc = _servos_gpio
    ga.angle = a
    gb.angle = b
    gc.angle = c


def execute_sort(label: str) -> None:
    """
    Run class-specific motion (simultaneous where multiple motors), hold MOTOR_HOLD_SEC,
    then reset all servos to home.
    """
    if config.SERVO_BACKEND == "servokit":
        if _kit is None:
            raise RuntimeError("motors not initialized")
    elif _servos_gpio is None:
        raise RuntimeError("motors not initialized")

    hold = config.MOTOR_HOLD_SEC
    reset_all()

    if label not in SORT_LABELS:
        raise ValueError(f"unknown label: {label!r}; expected one of {SORT_LABELS}")

    if label == "waste":
        _apply_angles(config.ANGLE_WASTE_A, config.ANGLE_WASTE_B, 0)
        logger.info(
            "sort motion: waste (A=%s B=%s) hold %.1fs",
            config.ANGLE_WASTE_A,
            config.ANGLE_WASTE_B,
            hold,
        )
    elif label == "recyclable":
        _apply_angles(0, config.ANGLE_RECYCLABLE_B, 0)
        logger.info(
            "sort motion: recyclable (B=%s) hold %.1fs",
            config.ANGLE_RECYCLABLE_B,
            hold,
        )
    elif label == "compost":
        _apply_angles(0, config.ANGLE_COMPOST_B, config.ANGLE_COMPOST_C)
        logger.info(
            "sort motion: compost (B=%s C=%s) hold %.1fs",
            config.ANGLE_COMPOST_B,
            config.ANGLE_COMPOST_C,
            hold,
        )
    time.sleep(hold)
    reset_all()
