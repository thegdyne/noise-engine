"""App path helpers (cross-platform).

SSOT for NoiseEngine app data/state paths.

Environment overrides (useful for portable/dev launches):
- NE_CFG_DIR: base dir containing config.scd + state/
- NE_STATE_DIR: explicit state dir (overrides NE_CFG_DIR/state)
"""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "NoiseEngine"


def _env_path(name: str) -> Path | None:
    v = os.environ.get(name)
    if not v:
        return None
    return Path(os.path.expanduser(v)).resolve()


def get_app_data_dir() -> Path:
    """Base app data dir."""
    cfg_dir = _env_path("NE_CFG_DIR")
    if cfg_dir is not None:
        return cfg_dir
    return Path(user_data_dir(APP_NAME, appauthor=False, roaming=True)).resolve()


def get_app_state_dir() -> Path:
    """State dir under the app data dir."""
    state_dir = _env_path("NE_STATE_DIR")
    if state_dir is not None:
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    state_dir = get_app_data_dir() / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_ready_json_path() -> Path:
    return get_app_state_dir() / "ready.json"


def get_sc_pid_path() -> Path:
    return get_app_state_dir() / "sc.pid"
