# Hardware — Raspberry Pi trash-sorting actuator + sensor daemon

## Overview

The Raspberry Pi runs **calibration** (ultrasonic average over 5 seconds with **LED1** blinking), then starts a **WebSocket server**. The **laptop server** ([`../server/`](../server/)) connects, receives the calibrated baseline in a `ready` message, polls distance, runs the CNN on its own camera, and sends **`execute_sort`** commands. This folder implements **only** GPIO: ultrasonic reads, three **AngularServo** outputs (MotorA/B/C), LED, and the JSON protocol in [`../shared/protocol.py`](../shared/protocol.py).

## Software architecture

### Configuration ([`config.py`](config.py))

| Category | Contents |
|----------|----------|
| **GPIO** | Ultrasonic TRIG/ECHO, LED1, `SERVO_MOTOR_A/B/C_PIN` (BCM), servo angle limits |
| **Ultrasonic** | `ULTRASONIC_MAX_DISTANCE_M` |
| **Calibration** | Duration, sample interval |
| **WebSocket** | `WS_HOST` (e.g. `0.0.0.0`), `WS_PORT` (default `8765`) |
| **Sort motion** | `MOTOR_HOLD_SEC` (2 s), per-class angles (`ANGLE_WASTE_*`, `ANGLE_RECYCLABLE_B`, `ANGLE_COMPOST_*`) |

### Modules

| Module | Role |
|--------|------|
| [`main.py`](main.py) | Calibrate → async WebSocket server (runs until interrupted) |
| [`ws_service.py`](ws_service.py) | `websockets` server: `get_distance`, `execute_sort` |
| [`calibration.py`](calibration.py) | Mean distance over window; blink LED1 |
| [`distance.py`](distance.py) | HC-SR04 via gpiozero `DistanceSensor` |
| [`motors.py`](motors.py) | `execute_sort(label)`: simultaneous holds per class, then reset to 0° |

### Sort motions (Pi)

- **waste**: MotorA +90°, MotorB +45°, hold **2 s** (simultaneous), then all servos to home (0°).
- **recyclable**: MotorB +90°, hold **2 s**, then reset.
- **compost**: MotorC +90°, MotorB −45°, hold **2 s**, then reset.

After each `execute_sort`, the Pi reads the ultrasonic once and returns **`sort_result`** with `cm` so the server can retry if still “occupied.”

### WebSocket messages

See [`../shared/protocol.py`](../shared/protocol.py). After a client connects, the Pi sends `{"type":"ready","calibrated_avg_cm":...}`. The server sends `get_distance` or `execute_sort` with `label`.

## Hardware notes

- **Sensing**: Ultrasonic (e.g. HC-SR04): respect 3.3 V–safe wiring for ECHO into the Pi.
- **Indication**: LED + resistor on **LED1**.
- **Actuation**: Three hobby **servos** (one signal pin each). Motor power must not back-feed the Pi; follow your servo/driver datasheet for supply and common ground.

## Building and running (Raspberry Pi OS)

### Prerequisites

- Python **3.11+**
- GPIO access (`gpio` group if needed)

### Virtual environment

```bash
cd hardware
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies: **`gpiozero`**, **`websockets`** (no PyTorch/OpenCV on the Pi).

### GPIO on Pi 5

If gpiozero misbehaves on Pi 5, see the [gpiozero Pi 5 notes](https://gpiozero.readthedocs.io/en/stable/).

### Run

From the **`hardware`** directory (so imports resolve; the repo root must be on `sys.path` for `shared` — `main.py` appends the parent folder automatically):

```bash
source .venv/bin/activate
python main.py
```

Point the laptop at **`ws://<pi-hostname-or-ip>:8765`** in [`server/config.py`](../server/config.py) (`WS_URL`).

## Repository layout

```
hardware/
  README.MD
  config.py
  main.py
  requirements.txt
  calibration.py
  distance.py
  motors.py
  ws_service.py
../shared/
  protocol.py
```
