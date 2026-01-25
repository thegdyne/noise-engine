"""Pytest configuration - PyQt5 mock for remaining tests.

This is a minimal conftest.py to allow non-unified-bus tests to run.
Will be replaced with full version in TEST_SUITE_REBUILD_PLAN.md Phase B.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# =============================================================================
# PyQt5 Mock Setup - MUST be before any test imports
# =============================================================================

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


@pytest.fixture(scope="session", autouse=True)
def set_working_directory():
    """Ensure tests run from project root."""
    os.chdir(ROOT)
    yield


@pytest.fixture(scope="session")
def project_root():
    """Return the project root path."""
    return ROOT


@pytest.fixture(scope="session")
def generators_dir(project_root):
    """Return the generators config directory path."""
    return project_root / "packs" / "core" / "generators"


@pytest.fixture(scope="session")
def supercollider_dir(project_root):
    """Return the supercollider directory path."""
    return project_root / "supercollider"


@pytest.fixture(scope="session")
def config_dir(project_root):
    """Return the config directory path."""
    return project_root / "config"
