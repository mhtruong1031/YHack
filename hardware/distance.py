"""Simulated distance (cm): no ultrasonic hardware; protocol-compatible with the laptop server."""

import config


def init_sensor() -> None:
    """No-op (kept for ws_service compatibility)."""


def close_sensor() -> None:
    """No-op."""


def read_cm() -> float:
    """Return configured simulated distance in centimeters."""
    return float(config.SIMULATED_DISTANCE_CM)
