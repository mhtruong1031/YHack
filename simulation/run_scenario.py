"""
Integration scenario: virtual Pi + server/main.py + harness WebSocket clients.

Starts ``run_virtual_pi`` first, then ``server/main.py`` with WS_URL pointing at the sim.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import websockets

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import server.config as srv_config
from shared.protocol import TYPE_ERROR, TYPE_READY
from simulation import config as sim_config
from simulation.pin_protocol import (
    TYPE_GET_PIN_OUTPUTS,
    TYPE_PIN_INPUT,
    TYPE_PIN_OUTPUTS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _load_scenario(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _scenario_duration_sec(scenario: dict) -> float:
    steps = scenario.get("steps") or []
    delays = sum(float(s.get("delay_sec", 0)) for s in steps)
    tail = float(scenario.get("tail_sec", 5.0))
    return delays + tail


async def _discard_ready(ws) -> None:
    raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    hello = json.loads(raw)
    if hello.get("type") != TYPE_READY:
        raise RuntimeError(f"expected {TYPE_READY}, got {hello!r}")


async def _poll_outputs_loop(uri: str, samples: list[dict], duration_sec: float) -> None:
    deadline = time.monotonic() + duration_sec
    last_pins: dict | None = None
    async with websockets.connect(uri) as ws:
        await _discard_ready(ws)
        while time.monotonic() < deadline:
            await ws.send(json.dumps({"type": TYPE_GET_PIN_OUTPUTS}))
            raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            if data.get("type") == TYPE_PIN_OUTPUTS:
                pins = dict(data.get("pins") or {})
                samples.append({"t": time.monotonic(), "pins": pins})
                if pins != last_pins:
                    logger.info("harness pin_outputs %s", pins)
                    last_pins = dict(pins)
            elif data.get("type") == TYPE_ERROR:
                logger.warning("poll pin_outputs error: %s", data.get("message"))
            await asyncio.sleep(0.05)


async def _steps_loop(uri: str, scenario: dict) -> None:
    steps = scenario.get("steps") or []
    tail_sec = float(scenario.get("tail_sec", 5.0))
    async with websockets.connect(uri) as ws:
        await _discard_ready(ws)
        for step in steps:
            await asyncio.sleep(float(step.get("delay_sec", 0)))
            desc = step.get("description")
            if desc:
                logger.info("scenario step: %s", desc)
            for pi in step.get("pin_inputs") or []:
                bcm = int(pi["bcm"])
                val = pi["value"]
                logger.info("harness pin_input bcm=%s value=%s", bcm, val)
                await ws.send(
                    json.dumps({"type": TYPE_PIN_INPUT, "bcm": bcm, "value": val})
                )
        await asyncio.sleep(tail_sec)


async def _run_harness(uri: str, scenario: dict) -> list[dict]:
    duration = _scenario_duration_sec(scenario)
    # Poller may start slightly after the stepper; keep sampling past steps+tail.
    poll_duration = duration + 3.0
    samples: list[dict] = []
    await asyncio.gather(
        _poll_outputs_loop(uri, samples, poll_duration),
        _steps_loop(uri, scenario),
    )
    return samples


def _check_expected(samples: list[dict], expected: dict) -> tuple[bool, list[str]]:
    errs: list[str] = []
    tol = 1.5
    if not samples:
        return False, ["no output samples collected"]

    pin_rows = [s["pins"] for s in samples]

    max_spec = expected.get("max_during_sort")
    if max_spec:
        for k, exp_v in max_spec.items():
            sk = str(k)
            vals = [float(row.get(sk, 0)) for row in pin_rows]
            mx = max(vals) if vals else 0.0
            if abs(mx - float(exp_v)) > tol:
                errs.append(
                    f"max_during_sort pin {sk}: expected ~{exp_v}, observed max {mx}"
                )

    final_spec = expected.get("final_pins")
    if final_spec:
        tail_n = min(20, len(samples))
        tail = samples[-tail_n:]
        for k, exp_v in final_spec.items():
            sk = str(k)
            avg = sum(float(s["pins"].get(sk, 0)) for s in tail) / len(tail)
            if abs(avg - float(exp_v)) > tol:
                errs.append(
                    f"final_pins pin {sk}: expected ~{exp_v}, tail avg {avg} (n={tail_n})"
                )

    return len(errs) == 0, errs


async def _wait_for_sim(uri: str, attempts: int = 40, gap: float = 0.15) -> None:
    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            async with websockets.connect(uri) as ws:
                await _discard_ready(ws)
            logger.info("sim WebSocket ready at %s (attempt %s)", uri, i + 1)
            return
        except BaseException as e:
            last_exc = e
            await asyncio.sleep(gap)
    raise RuntimeError(f"sim not reachable at {uri!r}: {last_exc!r}")


def main() -> int:
    sim_dir = Path(__file__).resolve().parent
    default_json = sim_dir / "scenarios" / "waste_proximity.json"
    parser = argparse.ArgumentParser(description="Run simulation integration scenario")
    parser.add_argument(
        "--scenario",
        type=Path,
        default=default_json,
        help="Path to scenario JSON",
    )
    args = parser.parse_args()
    scenario_path = args.scenario.resolve()

    scenario = _load_scenario(scenario_path)
    baseline_cm = float(scenario.get("baseline_cm", sim_config.SIM_BASELINE_CM))

    ws_uri = f"ws://{sim_config.SIM_WS_HOST}:{sim_config.SIM_WS_PORT}"
    env_base = os.environ.copy()
    env_base["PYTHONPATH"] = str(_REPO_ROOT)

    proc_pi: subprocess.Popen | None = None
    proc_srv: subprocess.Popen | None = None
    try:
        logger.info("Starting virtual Pi: %s", ws_uri)
        proc_pi = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "simulation.run_virtual_pi",
                "--baseline-cm",
                str(baseline_cm),
            ],
            cwd=str(_REPO_ROOT),
            env=env_base,
            stdout=None,
            stderr=None,
        )
        time.sleep(0.5)
        asyncio.run(_wait_for_sim(ws_uri))

        env_srv = env_base.copy()
        env_srv["WS_URL"] = ws_uri
        main_py = _REPO_ROOT / "server" / "main.py"
        logger.info("Starting server: %s", main_py)
        proc_srv = subprocess.Popen(
            [sys.executable, str(main_py)],
            cwd=str(_REPO_ROOT),
            env=env_srv,
            stdout=None,
            stderr=None,
        )
        time.sleep(1.0)

        logger.info(
            "Server timing: MAIN_LOOP_INTERVAL_SEC=%s PROXIMITY_HOLD_SEC=%s (scenario steps+tail=%.2fs)",
            srv_config.MAIN_LOOP_INTERVAL_SEC,
            srv_config.PROXIMITY_HOLD_SEC,
            _scenario_duration_sec(scenario),
        )
        logger.info("Running harness (duration ~%.2fs)", _scenario_duration_sec(scenario))
        samples = asyncio.run(_run_harness(ws_uri, scenario))

        ok, errs = _check_expected(samples, scenario.get("expected") or {})
        if ok:
            logger.info("SCENARIO PASS (%s samples)", len(samples))
            print("PASS")
            return 0
        logger.error("SCENARIO FAIL: %s", errs)
        for e in errs:
            print("FAIL:", e)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130
    finally:
        if proc_srv is not None and proc_srv.poll() is None:
            proc_srv.terminate()
            try:
                proc_srv.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc_srv.kill()
        if proc_pi is not None and proc_pi.poll() is None:
            proc_pi.terminate()
            try:
                proc_pi.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc_pi.kill()


if __name__ == "__main__":
    raise SystemExit(main())
