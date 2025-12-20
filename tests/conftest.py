"""Pytest configuration - ensure consistent CWD and provide fixtures.

Some code paths (OSC registration) currently resolve filesystem paths relative
to the current working directory. Running pytest from `tests/` or elsewhere
can therefore skip route registration.

This is intentionally a test-only stabilizer; the proper fix is to make
runtime code CWD-independent (backlog item).
"""
from __future__ import annotations

import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def pytest_sessionstart(session):
    os.chdir(ROOT)


# Fixtures used by multiple test files

@pytest.fixture
def project_root():
    """Return path to project root."""
    return ROOT


@pytest.fixture
def generators_dir():
    """Return path to supercollider/generators directory."""
    return ROOT / "supercollider" / "generators"


@pytest.fixture
def supercollider_dir():
    """Return path to supercollider directory."""
    return ROOT / "supercollider"
