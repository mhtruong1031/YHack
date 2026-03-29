"""WebSocket protocol against mock Pi (no server orchestrator)."""

from __future__ import annotations

import json

import pytest
import websockets

from shared.protocol import (
    SORT_LABELS,
    TYPE_DISTANCE,
    TYPE_ERROR,
    TYPE_EXECUTE_SORT,
    TYPE_GET_DISTANCE,
    TYPE_READY,
    TYPE_SORT_RESULT,
)

from tests.e2e.mock_pi import mock_pi_server


@pytest.mark.asyncio
async def test_ready_and_get_distance():
    async with mock_pi_server(calibrated_avg_cm=55.5) as (uri, state):
        state.set_distance_cm(42.0)
        async with websockets.connect(uri) as ws:
            raw = await ws.recv()
            msg = json.loads(raw)
            assert msg["type"] == TYPE_READY
            assert msg["calibrated_avg_cm"] == 55.5

            await ws.send(json.dumps({"type": TYPE_GET_DISTANCE}))
            raw2 = await ws.recv()
            resp = json.loads(raw2)
            assert resp["type"] == TYPE_DISTANCE
            assert resp["cm"] == 42.0


@pytest.mark.asyncio
@pytest.mark.parametrize("label", SORT_LABELS)
async def test_execute_sort_each_label(label: str):
    async with mock_pi_server() as (uri, state):
        state.set_distance_cm(80.0)
        async with websockets.connect(uri) as ws:
            await ws.recv()  # ready

            await ws.send(
                json.dumps({"type": TYPE_EXECUTE_SORT, "label": label})
            )
            raw = await ws.recv()
            resp = json.loads(raw)
            assert resp["type"] == TYPE_SORT_RESULT
            assert resp["cm"] == 80.0
            assert state.execute_sort_calls == [label]


@pytest.mark.asyncio
async def test_invalid_json_returns_error():
    async with mock_pi_server() as (uri, _state):
        async with websockets.connect(uri) as ws:
            await ws.recv()
            await ws.send("not-json{{{")
            raw = await ws.recv()
            resp = json.loads(raw)
            assert resp["type"] == TYPE_ERROR
            assert "invalid JSON" in resp["message"]


@pytest.mark.asyncio
async def test_unknown_type():
    async with mock_pi_server() as (uri, _state):
        async with websockets.connect(uri) as ws:
            await ws.recv()
            await ws.send(json.dumps({"type": "nope"}))
            raw = await ws.recv()
            resp = json.loads(raw)
            assert resp["type"] == TYPE_ERROR
            assert "unknown type" in resp["message"]


@pytest.mark.asyncio
async def test_execute_sort_missing_label():
    async with mock_pi_server() as (uri, _state):
        async with websockets.connect(uri) as ws:
            await ws.recv()
            await ws.send(json.dumps({"type": TYPE_EXECUTE_SORT}))
            raw = await ws.recv()
            resp = json.loads(raw)
            assert resp["type"] == TYPE_ERROR
            assert "missing label" in resp["message"]


@pytest.mark.asyncio
async def test_execute_sort_unknown_label():
    async with mock_pi_server() as (uri, state):
        async with websockets.connect(uri) as ws:
            await ws.recv()
            await ws.send(
                json.dumps({"type": TYPE_EXECUTE_SORT, "label": "metal"})
            )
            raw = await ws.recv()
            resp = json.loads(raw)
            assert resp["type"] == TYPE_ERROR
            assert "unknown label" in resp["message"]
            assert state.execute_sort_calls == []
