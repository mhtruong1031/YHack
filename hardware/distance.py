"""Ultrasonic distance reads using config pin assignments."""

from gpiozero import DistanceSensor

import config

_sensor: DistanceSensor | None = None


def init_sensor() -> None:
    global _sensor
    if _sensor is not None:
        return
    _sensor = DistanceSensor(
        trigger=config.ULTRASONIC_TRIG_PIN,
        echo=config.ULTRASONIC_ECHO_PIN,
        max_distance=config.ULTRASONIC_MAX_DISTANCE_M,
    )


def close_sensor() -> None:
    global _sensor
    if _sensor is not None:
        _sensor.close()
        _sensor = None


def read_cm() -> float:
    """Return distance in centimeters (gpiozero reports meters)."""
    if _sensor is None:
        init_sensor()
    assert _sensor is not None
    return float(_sensor.distance * 100.0)
