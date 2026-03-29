# Hardware — Raspberry Pi trash-sorting actuator daemon

## Overview

The Raspberry Pi runs a **WebSocket server** (no ultrasonic hardware in this tree). **`get_distance`** returns a **configurable simulated** distance in cm. **`execute_sort`** runs the same **subprocess** you would run by hand — **`servo_test3.py`** / **`servo_test4.py`** / **`servo_test5.py`** — for **recyclable** / **waste** / **compost** (only **one** script at a time, global lock). The **laptop server** ([`../server/`](../server/)) connects, receives `calibrated_avg_cm` in `ready`, and sends **`execute_sort`** with a label. Protocol: [`../shared/protocol.py`](../shared/protocol.py).

## Software architecture

### Configuration ([`config.py`](config.py))

| Category | Contents |
|----------|----------|
| **Simulated distance** | `SIMULATED_DISTANCE_CM`, `SIMULATED_CALIBRATED_AVG_CM` (for `ready` baseline) |
| **WebSocket** | `WS_HOST`, `WS_PORT` (default `8765`) |
| **Scripts** | `MOTOR_SCRIPT_TIMEOUT_SEC` (env, default **120**) — max seconds per `servo_test*.py` run |

### Modules

| Module | Role |
|--------|------|
| [`main.py`](main.py) | Start WebSocket server with simulated baseline |
| [`ws_service.py`](ws_service.py) | `websockets` server: `get_distance`, `execute_sort` (sort runs in a thread pool so long scripts don’t stall pings) |
| [`distance.py`](distance.py) | Returns `SIMULATED_DISTANCE_CM` (no sensor) |
| [`motors.py`](motors.py) | `execute_sort(label)` → `subprocess` of `servo_test3/4/5.py` |

### Sort motions (Pi)

| Label | Script |
|-------|--------|
| recyclable | [`servo_test3.py`](servo_test3.py) |
| waste | [`servo_test4.py`](servo_test4.py) |
| compost | [`servo_test5.py`](servo_test5.py) |

Edit those files to change motion; `execute_sort` does not duplicate their logic.

### Proximity on the laptop

The server treats “occupied” when `distance < calibrated_avg_cm − PROXIMITY_MARGIN_CM`. With default simulated **100 cm** read and **100 cm** baseline, proximity **does not** trigger sorts; use **camera / lighting** triggers on the laptop, or lower `SIMULATED_DISTANCE_CM` below `SIMULATED_CALIBRATED_AVG_CM − margin` if you want the Pi path to fire without a real sensor.

## Hardware notes

- **Actuation**: Same setup as your working **`servo_test*.py`** runs (e.g. Adafruit Servo HAT / PCA9685). Motor power must not back-feed the Pi; common ground and appropriate supply per datasheet.

## Building and running (Raspberry Pi OS)

### Prerequisites

- Python **3.11+**
- I2C enabled if using Servo HAT (`adafruit-circuitpython-servokit`)

### Virtual environment

```bash
cd hardware
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies: **`websockets`**, **`adafruit-circuitpython-servokit`** (for `servo_test*.py`), **`RPi.GPIO`** (optional GPIO experiments).

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
  servo_test3.py … servo_test5.py
../shared/
  protocol.py
```
