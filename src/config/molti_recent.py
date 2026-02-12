"""
MOLTI-SAMP recent files store.

Persists a list of recently loaded .korgmultisample file paths
for quick re-access via the LOAD button context menu.

Storage: ~/.noise-engine/molti_recent.json
"""

import json
from pathlib import Path
from typing import List

MAX_RECENT = 10
_STORE_PATH = Path.home() / ".noise-engine" / "molti_recent.json"


def _load_store() -> List[str]:
    """Load recent files list from disk."""
    if not _STORE_PATH.exists():
        return []
    try:
        data = json.loads(_STORE_PATH.read_text())
        if isinstance(data, list):
            return [str(p) for p in data if p]
        return []
    except Exception:
        return []


def _save_store(recent: List[str]):
    """Save recent files list to disk."""
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(recent[:MAX_RECENT], indent=2))


def get_recent_files() -> List[str]:
    """Get list of recent .korgmultisample file paths (newest first)."""
    return _load_store()


def add_recent_file(filepath) -> None:
    """Add a file path to the recent list (moves to top if already present)."""
    filepath = str(filepath)
    recent = _load_store()
    if filepath in recent:
        recent.remove(filepath)
    recent.insert(0, filepath)
    _save_store(recent[:MAX_RECENT])
