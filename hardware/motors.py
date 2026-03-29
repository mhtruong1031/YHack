"""Run per-label servo demo scripts (same as manual `python servo_test3.py` on the Pi)."""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
from pathlib import Path

import config
from shared.protocol import SORT_LABELS

logger = logging.getLogger(__name__)

_HW_DIR = Path(__file__).resolve().parent

_SORT_SCRIPT_BY_LABEL: dict[str, str] = {
    "recyclable": "servo_test3.py",
    "waste": "servo_test4.py",
    "compost": "servo_test5.py",
}

_script_lock = threading.Lock()


def init_motors() -> None:
    logger.info(
        "motors: execute_sort runs subprocess scripts in %s (one at a time)",
        _HW_DIR,
    )
    for label, name in _SORT_SCRIPT_BY_LABEL.items():
        p = _HW_DIR / name
        if not p.is_file():
            logger.warning("motors: missing %s for label=%s", p, label)


def close_motors() -> None:
    pass


def execute_sort(label: str) -> None:
    if label not in SORT_LABELS:
        raise ValueError(f"unknown label: {label!r}; expected one of {SORT_LABELS}")

    name = _SORT_SCRIPT_BY_LABEL[label]
    script = _HW_DIR / name
    if not script.is_file():
        raise FileNotFoundError(f"motor script not found: {script}")

    with _script_lock:
        logger.info("motors: starting %s (label=%s)", name, label)
        subprocess.run(
            [sys.executable, str(script)],
            cwd=str(_HW_DIR),
            check=True,
            timeout=config.MOTOR_SCRIPT_TIMEOUT_SEC,
        )
        logger.info("motors: finished %s", name)
