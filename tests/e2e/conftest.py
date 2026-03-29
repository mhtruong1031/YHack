"""Shared fixtures and fast server config for E2E tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SERVER_DIR = _REPO_ROOT / "server"
# server/main.py and server/api_client.py expect plain `analysis` / `config` (run from server/).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_SERVER_DIR) not in sys.path:
    sys.path.append(str(_SERVER_DIR))


@pytest.fixture(autouse=True)
def _e2e_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Headless analysis path; no Gemini key in E2E."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture
def fast_server_config(monkeypatch: pytest.MonkeyPatch):
    """Tight timing and no lighting thread (no camera)."""
    # Same module object as `import config` inside server/main.py (server/ on sys.path).
    import config as srv_config

    monkeypatch.setattr(srv_config, "LIGHTING_TRIGGER_ENABLED", False)
    monkeypatch.setattr(srv_config, "MAIN_LOOP_INTERVAL_SEC", 0.02)
    monkeypatch.setattr(srv_config, "PROXIMITY_HOLD_SEC", 0.06)
    monkeypatch.setattr(srv_config, "SORT_COOLDOWN_SEC", 0.0)
    monkeypatch.setattr(srv_config, "HARDWARE_SORT_SCRIPTS_ENABLED", False)
    return srv_config
