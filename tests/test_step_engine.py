"""
Step Engine Integration Tests

Tests for:
- Preset schema roundtrip of new step engine fields
- Migration backfill (old presets get defaults)
- Config OSC path validation
- MotionManager step mode handover
"""
import pytest
from dataclasses import fields
from unittest.mock import MagicMock, call

from src.presets.preset_schema import SlotState, PresetState
from src.config import OSC_PATHS, ARP_RATE_TO_FABRIC_IDX
from tests.helpers.state_helpers import autofill_nondefaults


# =============================================================================
# PRESET SCHEMA ROUNDTRIP
# =============================================================================

class TestStepEnginePresetRoundTrip:
    """Step engine fields survive serialization round-trip."""

    def test_slot_step_mode_round_trips(self):
        """SlotState.step_mode round-trips through to_dict/from_dict."""
        slot = SlotState(step_mode=True)
        restored = SlotState.from_dict(slot.to_dict())
        assert restored.step_mode is True

    def test_slot_arp_notes_round_trips(self):
        """SlotState.arp_notes round-trips through to_dict/from_dict."""
        notes = [60, 64, 67, 72]
        slot = SlotState(arp_notes=notes)
        restored = SlotState.from_dict(slot.to_dict())
        assert restored.arp_notes == notes

    def test_slot_arp_notes_empty_round_trips(self):
        """Empty arp_notes round-trips correctly."""
        slot = SlotState(arp_notes=[])
        restored = SlotState.from_dict(slot.to_dict())
        assert restored.arp_notes == []

    def test_preset_step_engine_enabled_round_trips(self):
        """PresetState.step_engine_enabled round-trips."""
        preset = PresetState(step_engine_enabled=True)
        d = preset.to_dict()
        assert d["step_engine_enabled"] is True
        restored = PresetState.from_dict(d)
        assert restored.step_engine_enabled is True

    def test_autofill_covers_step_fields(self):
        """autofill_nondefaults produces non-default values for step fields."""
        slot = autofill_nondefaults(SlotState)
        # step_mode default is False, autofill should make it True
        assert slot.step_mode is True
        # arp_notes default is [], autofill should make it non-empty
        assert len(slot.arp_notes) > 0

    def test_full_slot_roundtrip_includes_step_fields(self):
        """Full SlotState roundtrip covers step engine fields."""
        original = autofill_nondefaults(SlotState)
        restored = SlotState.from_dict(original.to_dict())
        assert restored.step_mode == original.step_mode
        assert restored.arp_notes == original.arp_notes


# =============================================================================
# MIGRATION / BACKWARD COMPAT
# =============================================================================

class TestStepEngineMigration:
    """Old presets without step engine fields get defaults."""

    def test_slot_missing_step_mode_gets_default(self):
        """Old slot data without step_mode gets False."""
        old_data = {"generator": "test", "params": {"frequency": 0.5}}
        slot = SlotState.from_dict(old_data)
        assert slot.step_mode is False

    def test_slot_missing_arp_notes_gets_empty(self):
        """Old slot data without arp_notes gets empty list."""
        old_data = {"generator": "test", "params": {}}
        slot = SlotState.from_dict(old_data)
        assert slot.arp_notes == []

    def test_preset_missing_step_engine_enabled_gets_default(self):
        """Old preset without step_engine_enabled gets False."""
        old_data = {
            "version": 3,
            "name": "Old Preset",
            "slots": [{}] * 8,
        }
        preset = PresetState.from_dict(old_data)
        assert preset.step_engine_enabled is False


# =============================================================================
# CONFIG OSC PATHS
# =============================================================================

class TestStepEngineOSCPaths:
    """Step engine OSC paths are properly configured."""

    def test_gen_step_mode_path_exists(self):
        """gen_step_mode OSC path exists."""
        assert 'gen_step_mode' in OSC_PATHS

    def test_arp_set_notes_path_exists(self):
        """arp_set_notes OSC path exists."""
        assert 'arp_set_notes' in OSC_PATHS

    def test_step_set_rate_path_exists(self):
        """step_set_rate OSC path exists."""
        assert 'step_set_rate' in OSC_PATHS

    def test_seq_set_bulk_path_exists(self):
        """seq_set_bulk OSC path exists."""
        assert 'seq_set_bulk' in OSC_PATHS

    def test_seq_set_play_mode_path_exists(self):
        """seq_set_play_mode OSC path exists."""
        assert 'seq_set_play_mode' in OSC_PATHS

    def test_step_event_path_exists(self):
        """step_event OSC path exists."""
        assert 'step_event' in OSC_PATHS

    def test_all_step_paths_use_noise_prefix(self):
        """All step engine OSC paths start with /noise/."""
        step_keys = [
            'gen_step_mode', 'arp_set_notes', 'step_set_rate',
            'seq_set_bulk', 'seq_set_play_mode', 'step_event',
        ]
        for key in step_keys:
            assert OSC_PATHS[key].startswith('/noise/'), \
                f"Step engine path '{key}' missing /noise/ prefix"

    def test_arp_rate_fabric_idx_mapping_complete(self):
        """Every ARP rate (0-6) has a fabric index mapping."""
        for rate_idx in range(7):
            assert rate_idx in ARP_RATE_TO_FABRIC_IDX, \
                f"ARP rate {rate_idx} missing from ARP_RATE_TO_FABRIC_IDX"


# =============================================================================
# MOTION MANAGER HANDOVER
# =============================================================================

class TestMotionManagerStepMode:
    """MotionManager sends step mode OSC during handover."""

    def _make_motion_manager(self, send_osc=None):
        """Create a MotionManager with mock dependencies."""
        from src.gui.arp_engine import ArpEngine
        from src.gui.motion_manager import MotionManager

        mock_send_note_on = MagicMock()
        mock_send_note_off = MagicMock()

        engines = []
        for i in range(8):
            eng = ArpEngine(
                slot_id=i,
                send_note_on=mock_send_note_on,
                send_note_off=mock_send_note_off,
                get_velocity=lambda: 64,
                get_bpm=lambda: 120.0,
            )
            engines.append(eng)

        mm = MotionManager(
            arp_engines=engines,
            send_note_on=mock_send_note_on,
            send_note_off=mock_send_note_off,
            get_bpm=lambda: 120.0,
            send_osc=send_osc,
        )
        return mm

    def test_set_mode_arp_sends_step_mode(self):
        """Entering ARP mode sends stepMode=1 to SC."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.ARP)

        # Should have sent gen_step_mode with slot=1 (1-indexed), mode=1
        step_mode_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['gen_step_mode']
        ]
        assert len(step_mode_calls) >= 1
        assert step_mode_calls[0] == call(OSC_PATHS['gen_step_mode'], [1, 1])

    def test_set_mode_seq_sends_step_mode(self):
        """Entering SEQ mode sends stepMode=2 to SC."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.SEQ)

        step_mode_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['gen_step_mode']
        ]
        assert len(step_mode_calls) >= 1
        assert step_mode_calls[0] == call(OSC_PATHS['gen_step_mode'], [1, 2])

    def test_set_mode_off_sends_step_mode_zero(self):
        """Exiting to OFF mode sends stepMode=0 to SC."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        # First enter ARP, then go to OFF
        mm.set_mode(0, MotionMode.ARP)
        mock_osc.reset_mock()

        mm.set_mode(0, MotionMode.OFF)

        step_mode_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['gen_step_mode']
        ]
        assert len(step_mode_calls) >= 1
        assert step_mode_calls[0] == call(OSC_PATHS['gen_step_mode'], [1, 0])

    def test_set_mode_arp_sends_rate(self):
        """Entering ARP mode sends step rate to SC."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.ARP)

        rate_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['step_set_rate']
        ]
        assert len(rate_calls) >= 1

    def test_no_osc_callback_no_crash(self):
        """MotionManager works without send_osc callback."""
        mm = self._make_motion_manager(send_osc=None)

        from src.model.sequencer import MotionMode
        # Should not raise
        mm.set_mode(0, MotionMode.ARP)
        mm.set_mode(0, MotionMode.OFF)
