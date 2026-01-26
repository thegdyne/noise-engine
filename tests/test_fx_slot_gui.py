"""
Tests for FX Slot GUI (UI Refresh Phase 2)

Validates the FX slot widget configuration and structure.
Note: Full GUI tests require PyQt5.
"""

import unittest
import os
import sys


class TestFxSlotConfig(unittest.TestCase):
    """Test FX slot configuration in config/__init__.py."""

    def test_fx_slot_types_defined(self):
        """FX_SLOT_TYPES is defined with expected values."""
        from src.config import FX_SLOT_TYPES
        self.assertIn('Empty', FX_SLOT_TYPES)
        self.assertIn('Echo', FX_SLOT_TYPES)
        self.assertIn('Reverb', FX_SLOT_TYPES)
        self.assertIn('Chorus', FX_SLOT_TYPES)
        self.assertIn('LoFi', FX_SLOT_TYPES)

    def test_fx_slot_param_labels(self):
        """FX_SLOT_PARAM_LABELS has 4 labels per type."""
        from src.config import FX_SLOT_TYPES, FX_SLOT_PARAM_LABELS
        for fx_type in FX_SLOT_TYPES:
            self.assertIn(fx_type, FX_SLOT_PARAM_LABELS,
                          f"Missing param labels for {fx_type}")
            self.assertEqual(len(FX_SLOT_PARAM_LABELS[fx_type]), 4,
                             f"{fx_type} should have 4 param labels")

    def test_fx_slot_defaults(self):
        """FX_SLOT_DEFAULTS has 4 default values per type."""
        from src.config import FX_SLOT_TYPES, FX_SLOT_DEFAULTS
        for fx_type in FX_SLOT_TYPES:
            self.assertIn(fx_type, FX_SLOT_DEFAULTS,
                          f"Missing defaults for {fx_type}")
            self.assertEqual(len(FX_SLOT_DEFAULTS[fx_type]), 4,
                             f"{fx_type} should have 4 default values")

    def test_fx_slot_default_types(self):
        """FX_SLOT_DEFAULT_TYPES has 4 entries."""
        from src.config import FX_SLOT_DEFAULT_TYPES
        self.assertEqual(len(FX_SLOT_DEFAULT_TYPES), 4)


class TestFxSlotFileExists(unittest.TestCase):
    """Test that FX slot GUI files exist."""

    def setUp(self):
        """Set up test paths."""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.gui_path = os.path.join(self.base_path, "src", "gui")

    def test_fx_slot_py_exists(self):
        """fx_slot.py exists."""
        path = os.path.join(self.gui_path, "fx_slot.py")
        self.assertTrue(os.path.exists(path), f"Missing: {path}")

    def test_fx_grid_py_exists(self):
        """fx_grid.py exists."""
        path = os.path.join(self.gui_path, "fx_grid.py")
        self.assertTrue(os.path.exists(path), f"Missing: {path}")


class TestFxSlotStructure(unittest.TestCase):
    """Test FX slot module structure."""

    def setUp(self):
        """Set up test paths."""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.gui_path = os.path.join(self.base_path, "src", "gui")

    def test_fx_slot_has_class(self):
        """fx_slot.py defines FXSlot class."""
        path = os.path.join(self.gui_path, "fx_slot.py")
        with open(path, 'r') as f:
            content = f.read()
        self.assertIn("class FXSlot", content)

    def test_fx_slot_has_signals(self):
        """fx_slot.py has required signals."""
        path = os.path.join(self.gui_path, "fx_slot.py")
        with open(path, 'r') as f:
            content = f.read()
        self.assertIn("type_changed = pyqtSignal", content)
        self.assertIn("param_changed = pyqtSignal", content)
        self.assertIn("bypass_changed = pyqtSignal", content)

    def test_fx_slot_has_layout(self):
        """fx_slot.py has SLOT_LAYOUT dict."""
        path = os.path.join(self.gui_path, "fx_slot.py")
        with open(path, 'r') as f:
            content = f.read()
        self.assertIn("SLOT_LAYOUT = {", content)

    def test_fx_grid_has_class(self):
        """fx_grid.py defines FXGrid class."""
        path = os.path.join(self.gui_path, "fx_grid.py")
        with open(path, 'r') as f:
            content = f.read()
        self.assertIn("class FXGrid", content)

    def test_fx_grid_creates_4_slots(self):
        """fx_grid.py creates 4 FXSlot instances."""
        path = os.path.join(self.gui_path, "fx_grid.py")
        with open(path, 'r') as f:
            content = f.read()
        self.assertIn("for i in range(1, 5):", content)
        self.assertIn("FXSlot(i", content)


class TestFxSlotOSCPaths(unittest.TestCase):
    """Test that OSC paths follow expected pattern."""

    def test_fx_slot_osc_path_pattern(self):
        """fx_slot.py uses correct OSC path pattern."""
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_path, "src", "gui", "fx_slot.py")
        with open(path, 'r') as f:
            content = f.read()

        # Check for OSC path patterns
        self.assertIn("/noise/fx/slot/", content)
        self.assertIn("/type", content)
        self.assertIn("/bypass", content)


if __name__ == '__main__':
    unittest.main()
