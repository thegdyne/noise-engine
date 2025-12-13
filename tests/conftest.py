"""
Pytest configuration and shared fixtures
"""

import pytest
import os
import sys

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def generators_dir(project_root):
    """Return the generators directory path."""
    return os.path.join(project_root, 'supercollider', 'generators')


@pytest.fixture
def supercollider_dir(project_root):
    """Return the supercollider directory path."""
    return os.path.join(project_root, 'supercollider')
