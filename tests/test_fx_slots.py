"""
Tests for FX Slot System (UI Refresh Phase 1)

Validates the 4-slot FX system infrastructure.
Note: These are structural tests - actual SC audio testing requires SC running.
"""

import unittest
import os


class TestFxSlotFiles(unittest.TestCase):
    """Test that all FX slot files exist."""

    def setUp(self):
        """Set up test paths."""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sc_path = os.path.join(self.base_path, "supercollider")

    def test_fx_slots_manager_exists(self):
        """fx_slots.scd manager file exists."""
        path = os.path.join(self.sc_path, "core", "fx_slots.scd")
        self.assertTrue(os.path.exists(path), f"Missing: {path}")

    def test_fx_empty_exists(self):
        """fx_empty.scd SynthDef exists."""
        path = os.path.join(self.sc_path, "effects", "fx_empty.scd")
        self.assertTrue(os.path.exists(path), f"Missing: {path}")

    def test_fx_echo_exists(self):
        """fx_echo.scd SynthDef exists."""
        path = os.path.join(self.sc_path, "effects", "fx_echo.scd")
        self.assertTrue(os.path.exists(path), f"Missing: {path}")

    def test_fx_reverb_exists(self):
        """fx_reverb.scd SynthDef exists."""
        path = os.path.join(self.sc_path, "effects", "fx_reverb.scd")
        self.assertTrue(os.path.exists(path), f"Missing: {path}")

    def test_fx_chorus_exists(self):
        """fx_chorus.scd SynthDef exists."""
        path = os.path.join(self.sc_path, "effects", "fx_chorus.scd")
        self.assertTrue(os.path.exists(path), f"Missing: {path}")

    def test_fx_lofi_exists(self):
        """fx_lofi.scd SynthDef exists."""
        path = os.path.join(self.sc_path, "effects", "fx_lofi.scd")
        self.assertTrue(os.path.exists(path), f"Missing: {path}")


class TestFxSlotSynthDefPattern(unittest.TestCase):
    """Test that FX slot SynthDefs follow the canonical pattern."""

    def setUp(self):
        """Set up test paths."""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sc_path = os.path.join(self.base_path, "supercollider")
        self.effects_path = os.path.join(self.sc_path, "effects")

    def _read_file(self, filename):
        """Read an SC file."""
        path = os.path.join(self.effects_path, filename)
        with open(path, 'r') as f:
            return f.read()

    def test_fx_echo_has_canonical_params(self):
        """fx_echo.scd has p1-p4, returnLevel, bypass params."""
        content = self._read_file("fx_echo.scd")
        self.assertIn("p1=", content)
        self.assertIn("p2=", content)
        self.assertIn("p3=", content)
        self.assertIn("p4=", content)
        self.assertIn("returnLevel=", content)
        self.assertIn("bypass=", content)
        self.assertIn("\\fxSlot_echo", content)

    def test_fx_reverb_has_canonical_params(self):
        """fx_reverb.scd has p1-p4, returnLevel, bypass params."""
        content = self._read_file("fx_reverb.scd")
        self.assertIn("p1=", content)
        self.assertIn("p2=", content)
        self.assertIn("p3=", content)
        self.assertIn("p4=", content)
        self.assertIn("returnLevel=", content)
        self.assertIn("bypass=", content)
        self.assertIn("\\fxSlot_reverb", content)

    def test_fx_chorus_has_canonical_params(self):
        """fx_chorus.scd has p1-p4, returnLevel, bypass params."""
        content = self._read_file("fx_chorus.scd")
        self.assertIn("p1=", content)
        self.assertIn("p2=", content)
        self.assertIn("p3=", content)
        self.assertIn("p4=", content)
        self.assertIn("returnLevel=", content)
        self.assertIn("bypass=", content)
        self.assertIn("\\fxSlot_chorus", content)

    def test_fx_lofi_has_canonical_params(self):
        """fx_lofi.scd has p1-p4, returnLevel, bypass params."""
        content = self._read_file("fx_lofi.scd")
        self.assertIn("p1=", content)
        self.assertIn("p2=", content)
        self.assertIn("p3=", content)
        self.assertIn("p4=", content)
        self.assertIn("returnLevel=", content)
        self.assertIn("bypass=", content)
        self.assertIn("\\fxSlot_lofi", content)

    def test_fx_empty_has_canonical_params(self):
        """fx_empty.scd has p1-p4, returnLevel, bypass params."""
        content = self._read_file("fx_empty.scd")
        self.assertIn("p1=", content)
        self.assertIn("p2=", content)
        self.assertIn("p3=", content)
        self.assertIn("p4=", content)
        self.assertIn("returnLevel=", content)
        self.assertIn("bypass=", content)
        self.assertIn("\\fxSlot_empty", content)


class TestBusesUpdate(unittest.TestCase):
    """Test that buses.scd has 4 FX send/return pairs."""

    def setUp(self):
        """Set up test paths."""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.buses_path = os.path.join(self.base_path, "supercollider", "core", "buses.scd")

    def test_buses_has_fx3_fx4(self):
        """buses.scd has fx3 and fx4 send/return buses."""
        with open(self.buses_path, 'r') as f:
            content = f.read()

        self.assertIn("~fx1SendBus", content)
        self.assertIn("~fx2SendBus", content)
        self.assertIn("~fx3SendBus", content)
        self.assertIn("~fx4SendBus", content)
        self.assertIn("~fx1ReturnBus", content)
        self.assertIn("~fx2ReturnBus", content)
        self.assertIn("~fx3ReturnBus", content)
        self.assertIn("~fx4ReturnBus", content)

    def test_buses_has_legacy_aliases(self):
        """buses.scd maintains legacy echo/verb aliases."""
        with open(self.buses_path, 'r') as f:
            content = f.read()

        self.assertIn("~echoSendBus = ~fx1SendBus", content)
        self.assertIn("~verbSendBus = ~fx2SendBus", content)
        self.assertIn("~echoReturnBus = ~fx1ReturnBus", content)
        self.assertIn("~verbReturnBus = ~fx2ReturnBus", content)

    def test_buses_has_arrays(self):
        """buses.scd has fxSendBuses and fxReturnBuses arrays."""
        with open(self.buses_path, 'r') as f:
            content = f.read()

        self.assertIn("~fxSendBuses", content)
        self.assertIn("~fxReturnBuses", content)


class TestFxMixerUpdate(unittest.TestCase):
    """Test that fx_mixer.scd handles 4 returns."""

    def setUp(self):
        """Set up test paths."""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.mixer_path = os.path.join(self.base_path, "supercollider", "core", "fx_mixer.scd")

    def test_mixer_has_4_returns(self):
        """fx_mixer.scd has 4 FX return parameters."""
        with open(self.mixer_path, 'r') as f:
            content = f.read()

        self.assertIn("fx1Return", content)
        self.assertIn("fx2Return", content)
        self.assertIn("fx3Return", content)
        self.assertIn("fx4Return", content)

    def test_mixer_has_4_return_buses(self):
        """fx_mixer.scd references 4 return buses."""
        with open(self.mixer_path, 'r') as f:
            content = f.read()

        self.assertIn("fx1ReturnBus", content)
        self.assertIn("fx2ReturnBus", content)
        self.assertIn("fx3ReturnBus", content)
        self.assertIn("fx4ReturnBus", content)


class TestInitScdUpdate(unittest.TestCase):
    """Test that init.scd loads FX slot system."""

    def setUp(self):
        """Set up test paths."""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.init_path = os.path.join(self.base_path, "supercollider", "init.scd")

    def test_init_loads_fx_slots(self):
        """init.scd loads fx_slots.scd."""
        with open(self.init_path, 'r') as f:
            content = f.read()

        self.assertIn('fx_slots.scd', content)
        self.assertIn('~setupFxSlots', content)
        self.assertIn('~startFxSlots', content)
        self.assertIn('~setupFxSlotsOSC', content)

    def test_init_loads_fx_synthdefs(self):
        """init.scd loads all FX SynthDef files."""
        with open(self.init_path, 'r') as f:
            content = f.read()

        self.assertIn('fx_empty.scd', content)
        self.assertIn('fx_echo.scd', content)
        self.assertIn('fx_reverb.scd', content)
        self.assertIn('fx_chorus.scd', content)
        self.assertIn('fx_lofi.scd', content)


class TestFxSlotsManager(unittest.TestCase):
    """Test FX slot manager structure."""

    def setUp(self):
        """Set up test paths."""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.slots_path = os.path.join(self.base_path, "supercollider", "core", "fx_slots.scd")

    def test_manager_has_slot_tracking(self):
        """fx_slots.scd has slot synth and type tracking."""
        with open(self.slots_path, 'r') as f:
            content = f.read()

        self.assertIn("~fxSlotSynths", content)
        self.assertIn("~fxSlotTypes", content)

    def test_manager_has_set_type_function(self):
        """fx_slots.scd has ~setFxSlotType function."""
        with open(self.slots_path, 'r') as f:
            content = f.read()

        self.assertIn("~setFxSlotType", content)

    def test_manager_has_osc_handlers(self):
        """fx_slots.scd has OSC handlers for slot control."""
        with open(self.slots_path, 'r') as f:
            content = f.read()

        self.assertIn("~setupFxSlotsOSC", content)
        self.assertIn("/noise/fx/slot/", content)


if __name__ == '__main__':
    unittest.main()
