"""Calibration: average distance over a window while LED1 blinks."""

import time

from gpiozero import LED

import config
import distance


def run_calibration() -> float:
    """
    Sample distance for CALIBRATION_DURATION_SEC while LED1 blinks.
    Returns mean distance in cm.
    """
    distance.init_sensor()
    led = LED(config.LED1_PIN)
    samples: list[float] = []
    deadline = time.monotonic() + config.CALIBRATION_DURATION_SEC
    blink_half = 0.2
    next_toggle = time.monotonic()

    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_toggle:
                led.toggle()
                next_toggle = now + blink_half
            try:
                samples.append(distance.read_cm())
            except Exception:
                pass
            time.sleep(config.CALIBRATION_SAMPLE_INTERVAL_SEC)
    finally:
        led.off()
        led.close()

    if not samples:
        raise RuntimeError("Calibration failed: no valid distance samples")
    return sum(samples) / len(samples)
