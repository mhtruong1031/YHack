# Hardware — Raspberry Pi trash-sorting actuator daemon

## Overview

The Raspberry Pi runs a **WebSocket server** (no ultrasonic hardware in this tree). **`get_distance`** returns a **configurable simulated** distance in cm; **`execute_sort`** drives three **AngularServo** outputs. The **laptop server** ([`../server/`](../server/)) connects, receives `calibrated_avg_cm` in `ready`, polls `get_distance`, runs vision on its camera, and sends **`execute_sort`** with a label. Protocol: [`../shared/protocol.py`](../shared/protocol.py).

## Software architecture

### Configuration ([`config.py`](config.py))

| Category | Contents |
|----------|----------|
| **GPIO** | `SERVO_MOTOR_A/B/C_PIN` (BCM), servo angle limits |
| **Simulated distance** | `SIMULATED_DISTANCE_CM`, `SIMULATED_CALIBRATED_AVG_CM` (for `ready` baseline) |
| **WebSocket** | `WS_HOST`, `WS_PORT` (default `8765`) |
| **Sort motion** | `MOTOR_HOLD_SEC`, per-class angles |

### Modules

| Module | Role |
|--------|------|
| [`main.py`](main.py) | Start WebSocket server with simulated baseline |
| [`ws_service.py`](ws_service.py) | `websockets` server: `get_distance`, `execute_sort` |
| [`distance.py`](distance.py) | Returns `SIMULATED_DISTANCE_CM` (no sensor) |
| [`motors.py`](motors.py) | `execute_sort(label)`: holds per class, then home 0° |

### Sort motions (Pi)

- **waste**: MotorA +90°, MotorB +45°, hold **2 s**, then home.
- **recyclable**: MotorB +90°, hold **2 s**, then home.
- **compost**: MotorC +90°, MotorB −45°, hold **2 s**, then home.

### Proximity on the laptop

The server treats “occupied” when `distance < calibrated_avg_cm − PROXIMITY_MARGIN_CM`. With default simulated **100 cm** read and **100 cm** baseline, proximity **does not** trigger sorts; use **camera / lighting** triggers on the laptop, or lower `SIMULATED_DISTANCE_CM` below `SIMULATED_CALIBRATED_AVG_CM − margin` if you want the Pi path to fire without a real sensor.

## Hardware notes

- **Actuation**: Three hobby **servos** (one signal pin each). Motor power must not back-feed the Pi; common ground and appropriate supply per datasheet.

## Building and running (Raspberry Pi OS)

### Prerequisites

- Python **3.11+**
- GPIO access for servos (`gpio` group if needed)

### Virtual environment

```bash
cd hardware
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies: **`gpiozero`**, **`websockets`**.

### GPIO on Pi 5

If gpiozero misbehaves on Pi 5, see the [gpiozero Pi 5 notes](https://gpiozero.readthedocs.io/en/stable/).

### Run

```bash
source .venv/bin/activate
python main.py
```

Point the laptop at **`ws://<pi-hostname-or-ip>:8765`** (`WS_URL` in [`../server/config.py`](../server/config.py)).

## Repository layout

```
hardware/
  README.MD
  config.py
  main.py
  requirements.txt
  distance.py
  motors.py
  ws_service.py
../shared/
  protocol.py
```
