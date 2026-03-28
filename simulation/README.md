# Simulation — virtual Raspberry Pi + integration harness

End-to-end exercise of the **hardware WebSocket surface** and **[`server/main.py`](../server/main.py)** without a physical Pi or GPIO. A **virtual Pi** process speaks the same JSON protocol as [`hardware/ws_service.py`](../hardware/ws_service.py) (`ready`, `get_distance`, `execute_sort`, `sort_result`, `error`). A separate **harness** connection drives and reads **virtual pins** only; it never talks to the laptop server directly.

## Layout

| File / directory | Role |
|------------------|------|
| [`config.py`](config.py) | Bind address (`127.0.0.1:18765`), short servo hold/reset timings, BCM and angle constants (aligned with [`hardware/config.py`](../hardware/config.py)). |
| [`pin_protocol.py`](pin_protocol.py) | Harness-only message types: `pin_input`, `get_pin_outputs`, `pin_outputs`. |
| [`virtual_gpio.py`](virtual_gpio.py) | Async shared state: simulated distance (cm), servo angles, LED. |
| [`sim_ws_service.py`](sim_ws_service.py) | `websockets` server: Pi protocol + pin protocol on one port, one shared `VirtualGPIO` across clients. |
| [`run_virtual_pi.py`](run_virtual_pi.py) | CLI entry: start the virtual Pi (`--baseline-cm` for the `ready` message). |
| [`run_scenario.py`](run_scenario.py) | Starts virtual Pi, then `server/main.py` with `WS_URL` set, runs the harness, asserts on logged pin samples. |
| [`scenarios/`](scenarios/) | JSON scenarios (steps, expected max/final pin values). |
| [`requirements.txt`](requirements.txt) | `websockets` (for the sim process; the server needs its own deps). |

## Protocols

**Laptop server → virtual Pi** (same as production; see [`shared/protocol.py`](../shared/protocol.py)):

- After connect, Pi sends `{"type":"ready","calibrated_avg_cm":...}`.
- Server sends `get_distance` → Pi replies `distance` with `cm`.
- Server sends `execute_sort` with `label` → Pi runs virtual sort motion → Pi replies `sort_result` with `cm`.

**Harness → virtual Pi** (simulation only; see [`pin_protocol.py`](pin_protocol.py)):

- `{"type":"pin_input","bcm":24,"value":<number>}` — BCM **24** (ECHO pin in hardware config) carries **simulated distance in centimeters**.
- Optional: `bcm` **17** (LED1), `value` **0** or **1**.
- `{"type":"get_pin_outputs"}` → `{"type":"pin_outputs","pins":{"5":...,"12":...,"19":...,"17":...}}` — servo angles in degrees on **5 / 12 / 19**, LED on **17**.

The server process must **not** send pin messages; only the harness uses them.

## Prerequisites

- Python **3.11+** (3.14 works with a venv).
- From the **repository root**, install sim + server dependencies (the scenario spawns `server/main.py`):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r simulation/requirements.txt -r server/requirements.txt
```

**Headless classification:** If `CNN_MODEL_WEIGHTS_PATH` is empty in [`server/config.py`](../server/config.py), [`server/analysis.py`](../server/analysis.py) skips the camera and uses a placeholder label (`waste`) and JPEG so the loop can run without a device.

**Pi URL for the server:** [`server/config.py`](../server/config.py) uses `WS_URL` from the environment when set; `run_scenario` sets it to `ws://127.0.0.1:18765`.

## Run the full scenario (recommended)

From the repo root, with `PYTHONPATH` pointing at the repo (the commands below rely on `-m` from root):

```bash
source .venv/bin/activate
python -m simulation.run_scenario
```

Optional scenario file:

```bash
python -m simulation.run_scenario --scenario simulation/scenarios/waste_proximity.json
```

The runner frees **TCP 18765** when possible (`lsof` on macOS), starts the virtual Pi, waits until the WebSocket accepts connections, starts the server subprocess, then runs two harness connections (pin steps + output polling). It logs each `pin_input` and logs `pin_outputs` when values change, then checks `expected` in the JSON. Exit code **0** prints `PASS`; failures print `FAIL:` lines.

## Run components manually

**1. Virtual Pi**

```bash
cd /path/to/YHack
source .venv/bin/activate
export PYTHONPATH="$PWD"
python -m simulation.run_virtual_pi --baseline-cm 50
```

**2. Laptop server** (another terminal, same venv / `PYTHONPATH`)

```bash
export PYTHONPATH="$PWD"
export WS_URL=ws://127.0.0.1:18765
python server/main.py
```

**3. Harness** — use any WebSocket client to send `pin_input` / `get_pin_outputs` JSON to the same URL, or adapt the logic in [`run_scenario.py`](run_scenario.py).

## Scenario JSON

| Field | Meaning |
|-------|---------|
| `baseline_cm` | Passed to `run_virtual_pi` and used in `ready` as `calibrated_avg_cm`. |
| `steps` | Ordered list of `{ "delay_sec", "description"?, "pin_inputs": [{ "bcm", "value" }] }`. |
| `tail_sec` | Extra wait after the last step before the harness finishes stepping. |
| `expected.max_during_sort` | Map pin string → expected **maximum** observed value over all samples (tolerance ~1.5°). |
| `expected.final_pins` | Map pin string → expected **average** over the last up to 20 samples (servos should be home after clearing distance). |

Keep simulated distance **below** `baseline_cm - PROXIMITY_MARGIN_CM` long enough for [`PROXIMITY_HOLD_SEC`](../server/config.py), then move distance **back above** threshold so the server does not loop sorts forever while you assert `final_pins`.

## See also

- [Hardware (real Pi)](../hardware/README.MD) — calibration, GPIO, production WebSocket behavior  
- [Server (laptop)](../server/README.MD) — proximity loop, CNN, config  
