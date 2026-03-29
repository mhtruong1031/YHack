"""Server orchestrator run_with_pi against mock Pi."""

from __future__ import annotations

import asyncio

import pytest
import websockets

from shared.protocol import SORT_LABELS

from tests.e2e.mock_pi import mock_pi_server


@pytest.mark.asyncio
async def test_proximity_triggers_sort_and_api_hooks(
    fast_server_config, monkeypatch: pytest.MonkeyPatch
):
    calls: list[tuple] = []

    monkeypatch.setattr(
        "server.main.api_client.notify_sort_result",
        lambda label: calls.append(("sort", label)),
    )
    monkeypatch.setattr(
        "server.main.api_client.notify_drop_image",
        lambda jpeg, classification=None: calls.append(
            ("drop", classification, len(jpeg))
        ),
    )

    from server.main import run_with_pi

    async with mock_pi_server(calibrated_avg_cm=100.0) as (uri, state):
        n = {"i": 0}

        def distance_fn():
            if state.execute_sort_calls:
                return 101.0
            n["i"] += 1
            if n["i"] <= 3:
                return 100.0
            return 90.0

        state.set_distance_fn(distance_fn)

        stop = asyncio.Event()
        async with websockets.connect(uri) as ws:
            task = asyncio.create_task(run_with_pi(ws, run_stop_event=stop))

            for _ in range(300):
                await asyncio.sleep(0.02)
                if state.execute_sort_calls:
                    break
            assert state.execute_sort_calls, "expected execute_sort from mock Pi"

            assert state.execute_sort_calls[0] == SORT_LABELS[0]
            assert any(x[0] == "sort" for x in calls)
            assert any(x[0] == "drop" for x in calls)

            stop.set()
            await asyncio.wait_for(task, timeout=10.0)


@pytest.mark.asyncio
async def test_max_sort_retries_when_distance_stays_low(
    fast_server_config, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        "server.main.api_client.notify_sort_result", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        "server.main.api_client.notify_drop_image", lambda *_a, **_k: None
    )

    from server.main import run_with_pi

    async with mock_pi_server(calibrated_avg_cm=100.0) as (uri, state):
        n = {"i": 0}

        def distance_fn():
            n["i"] += 1
            if n["i"] <= 3:
                return 100.0
            return 90.0

        state.set_distance_fn(distance_fn)

        stop = asyncio.Event()
        async with websockets.connect(uri) as ws:
            task = asyncio.create_task(run_with_pi(ws, run_stop_event=stop))

            for _ in range(400):
                await asyncio.sleep(0.02)
                if len(state.execute_sort_calls) >= 5:
                    break
            assert len(state.execute_sort_calls) == 5

            stop.set()
            await asyncio.wait_for(task, timeout=10.0)
