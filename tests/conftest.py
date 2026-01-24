"""Pytest configuration - ensure consistent CWD and provide fixtures.

Some code paths (OSC registration) currently resolve filesystem paths relative
to the current working directory. Running pytest from `tests/` or elsewhere
can therefore skip route registration.

This is intentionally a test-only stabilizer; the proper fix is to make
runtime code CWD-independent (backlog item).
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# =============================================================================
# PyQt5 Mock Setup - MUST be before any test imports mod_routing_state
# =============================================================================
# ModRoutingState inherits from QObject. Using a simple MagicMock for QObject
# causes StopIteration errors because MagicMock's internal iterators exhaust.
# The fix is to use a simple stub class instead.

class QObjectStub:
    """Minimal QObject stub for testing."""
    def __init__(self, parent=None):
        pass


def pyqtSignal_stub(*args, **kwargs):
    """Return a MagicMock that acts as a signal."""
    signal = MagicMock()
    signal.emit = MagicMock()
    signal.connect = MagicMock()
    return signal


# Set up the mock BEFORE any imports that might use PyQt5
mock_qt_core = MagicMock()
mock_qt_core.QObject = QObjectStub
mock_qt_core.pyqtSignal = pyqtSignal_stub
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtCore'] = mock_qt_core
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtGui'] = MagicMock()

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
    """Return path to core generators directory (packs/core/generators).
    
    Skips tests if the directory doesn't exist (e.g., in CI where packs may not be present).
    """
    path = ROOT / "packs" / "core" / "generators"
    if not path.exists():
        pytest.skip("packs/core/generators not present (likely CI environment)")
    return path


@pytest.fixture
def supercollider_dir():
    """Return path to supercollider directory."""
    return ROOT / "supercollider"
