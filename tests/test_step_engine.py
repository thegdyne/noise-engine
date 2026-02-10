"""
Step Engine Integration Tests

Tests for:
- Preset schema roundtrip of new step engine fields
- Migration backfill (old presets get defaults)
- Config OSC path validation
- MotionManager step mode handover
- v2: ARP clear on empty notes
- v2: SEQ bulk with gate field
- v2: envSource not sent from Python (D10: SC handles it)
- v2: ARP rate change propagates to SC
- v2: SEQ data changes propagate to SC during playback
"""
import pytest
from dataclasses import fields
from unittest.mock import MagicMock, call

from src.presets.preset_schema import SlotState, PresetState
from src.config import OSC_PATHS, ARP_RATE_TO_FABRIC_IDX
from src.model.sequencer import StepType, PlayMode
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


# =============================================================================
# v2: ARP CLEAR ON EMPTY NOTES
# =============================================================================

class TestMotionManagerARPClear:
    """v2: ARP always sends notes to SC, even when empty (clear signal)."""

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
        return mm, engines

    def test_arp_empty_notes_sends_osc(self):
        """Empty ARP notes still sends OSC (clear signal for SC buffer)."""
        mock_osc = MagicMock()
        mm, engines = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        # Enter ARP mode (no keys held = empty note list)
        mm.set_mode(0, MotionMode.ARP)

        # Should have sent arp_set_notes even with empty list
        arp_notes_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['arp_set_notes']
        ]
        assert len(arp_notes_calls) >= 1
        # Payload should be [slot_idx] with no notes (just the slot index)
        assert arp_notes_calls[0] == call(OSC_PATHS['arp_set_notes'], [0])

    def test_arp_with_notes_sends_notes(self):
        """ARP with held notes sends note list to SC."""
        mock_osc = MagicMock()
        mm, engines = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        # Simulate holding a key before entering ARP
        engines[0].key_press(60)
        mm.set_mode(0, MotionMode.ARP)

        arp_notes_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['arp_set_notes']
        ]
        assert len(arp_notes_calls) >= 1
        # Payload should include slot_idx + at least one note
        payload = arp_notes_calls[0][0][1]
        assert payload[0] == 0  # slot_idx
        assert len(payload) > 1  # has notes


# =============================================================================
# v2: SEQ BULK WITH GATE FIELD
# =============================================================================

class TestSEQBulkGate:
    """v2: SEQ bulk payload includes gate field (4 values per step)."""

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

    def test_seq_bulk_has_gate_field(self):
        """SEQ bulk payload has 4 values per step (type, note, vel, gate)."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.SEQ)

        bulk_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['seq_set_bulk']
        ]
        assert len(bulk_calls) >= 1
        payload = bulk_calls[0][0][1]
        # payload = [slot_idx, length, type1, note1, vel1, gate1, ...]
        slot_idx = payload[0]
        length = payload[1]
        step_data = payload[2:]
        # Each step has 4 values (type, note, vel, gate)
        assert len(step_data) == length * 4, \
            f"Expected {length * 4} values for {length} steps, got {len(step_data)}"

    def test_seq_bulk_gate_defaults_to_one(self):
        """Gate field defaults to 1.0 when SeqStep has no gate attr."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.SEQ)

        bulk_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['seq_set_bulk']
        ]
        assert len(bulk_calls) >= 1
        payload = bulk_calls[0][0][1]
        step_data = payload[2:]
        # Check first step's gate value (index 3 in each group of 4)
        if len(step_data) >= 4:
            gate = step_data[3]
            assert gate == 1.0, f"Expected gate=1.0, got {gate}"


# =============================================================================
# v2: ENVSOURCE NOT SENT FROM PYTHON (D10)
# =============================================================================

class TestEnvSourceNotSentFromPython:
    """v2: Python does NOT send envSource OSC — SC handles D10 auto-force."""

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

    def test_arp_mode_no_envsource_osc(self):
        """Entering ARP mode does NOT send envSource OSC from Python."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.ARP)

        # Check no envSource OSC was sent
        env_source_calls = [
            c for c in mock_osc.call_args_list
            if '/envSource' in str(c)
        ]
        assert len(env_source_calls) == 0, \
            f"Python should NOT send envSource OSC (D10: SC handles it), got: {env_source_calls}"

    def test_seq_mode_no_envsource_osc(self):
        """Entering SEQ mode does NOT send envSource OSC from Python."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.SEQ)

        env_source_calls = [
            c for c in mock_osc.call_args_list
            if '/envSource' in str(c)
        ]
        assert len(env_source_calls) == 0, \
            f"Python should NOT send envSource OSC (D10: SC handles it), got: {env_source_calls}"


# =============================================================================
# v2: ARP RATE CHANGE PROPAGATES TO SC
# =============================================================================

class TestARPRatePropagatesToSC:
    """v2: ARP rate changes push updated rate to SC step engine."""

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
        return mm, engines

    def test_arp_rate_change_sends_rate_osc(self):
        """Changing ARP rate while active sends updated rate to SC."""
        mock_osc = MagicMock()
        mm, engines = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        from src.gui.arp_engine import ArpEvent, ArpEventType

        # Enter ARP mode
        mm.set_mode(0, MotionMode.ARP)
        mock_osc.reset_mock()

        # Change rate (triggers _handle_rate_change → _notify_notes_changed → push)
        engines[0].post_event(ArpEvent(ArpEventType.RATE_CHANGE, {"rate_index": 3}))

        rate_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['step_set_rate']
        ]
        assert len(rate_calls) >= 1, \
            "ARP rate change should send step_set_rate OSC to SC"


# =============================================================================
# v2: SEQ DATA CHANGES PROPAGATE TO SC
# =============================================================================

class TestSEQDataPropagatesToSC:
    """v2: SEQ rate/play_mode/step changes push to SC during playback."""

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

    def test_seq_rate_change_sends_osc(self):
        """Changing SEQ rate while active sends updated data to SC."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.SEQ)
        mock_osc.reset_mock()

        # Change rate via command queue, then process commands via tick
        seq = mm.get_seq_engine(0)
        seq.set_rate(3)
        seq.tick(0.001)  # Process command queue

        rate_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['step_set_rate']
        ]
        assert len(rate_calls) >= 1, \
            "SEQ rate change should send step_set_rate OSC to SC"

    def test_seq_play_mode_change_sends_osc(self):
        """Changing SEQ play mode while active sends updated data to SC."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode, PlayMode
        mm.set_mode(0, MotionMode.SEQ)
        mock_osc.reset_mock()

        seq = mm.get_seq_engine(0)
        seq.set_play_mode(PlayMode.REVERSE)
        seq.tick(0.001)  # Process command queue

        play_mode_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['seq_set_play_mode']
        ]
        assert len(play_mode_calls) >= 1, \
            "SEQ play mode change should send seq_set_play_mode OSC to SC"

    def test_seq_step_edit_sends_osc(self):
        """Editing a SEQ step while active sends updated data to SC."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode, StepType
        mm.set_mode(0, MotionMode.SEQ)
        mock_osc.reset_mock()

        seq = mm.get_seq_engine(0)
        seq.queue_command({
            'type': 'SET_STEP',
            'index': 0,
            'step_type': StepType.NOTE,
            'note': 72,
            'velocity': 100,
        })
        seq.tick(0.001)  # Process command queue

        bulk_calls = [
            c for c in mock_osc.call_args_list
            if c[0][0] == OSC_PATHS['seq_set_bulk']
        ]
        assert len(bulk_calls) >= 1, \
            "SEQ step edit should send seq_set_bulk OSC to SC"

    def test_seq_callback_cleared_on_mode_exit(self):
        """SEQ on_data_changed callback is cleared when leaving SEQ mode."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.SEQ)
        seq = mm.get_seq_engine(0)
        assert seq.on_data_changed is not None

        mm.set_mode(0, MotionMode.OFF)
        assert seq.on_data_changed is None


# =============================================================================
# v2: PARAMETRIZED SEQ MUTATION → OSC PROPAGATION
# =============================================================================

# Every mutating command type must trigger on_data_changed → OSC push.
# If a new command type is added and forgets notify=True, this catches it.
SEQ_MUTATION_COMMANDS = [
    pytest.param(
        {'type': 'SET_STEP', 'index': 0, 'step_type': StepType.NOTE, 'note': 72, 'velocity': 100},
        id='SET_STEP',
    ),
    pytest.param(
        {'type': 'SET_LENGTH', 'length': 8},
        id='SET_LENGTH',
    ),
    pytest.param(
        {'type': 'SET_RATE', 'rate_index': 4},
        id='SET_RATE',
    ),
    pytest.param(
        {'type': 'SET_PLAY_MODE', 'play_mode': PlayMode.REVERSE},
        id='SET_PLAY_MODE',
    ),
    pytest.param(
        {'type': 'CLEAR_SEQUENCE'},
        id='CLEAR_SEQUENCE',
    ),
]


class TestSEQMutationPropagation:
    """Every SEQ mutation command must propagate to SC via on_data_changed."""

    def _make_motion_manager(self, send_osc=None):
        from src.gui.arp_engine import ArpEngine
        from src.gui.motion_manager import MotionManager

        mock_fn = MagicMock()
        engines = []
        for i in range(8):
            engines.append(ArpEngine(
                slot_id=i,
                send_note_on=mock_fn,
                send_note_off=mock_fn,
                get_velocity=lambda: 64,
                get_bpm=lambda: 120.0,
            ))
        return MotionManager(
            arp_engines=engines,
            send_note_on=mock_fn,
            send_note_off=mock_fn,
            get_bpm=lambda: 120.0,
            send_osc=send_osc,
        )

    @pytest.mark.parametrize("cmd", SEQ_MUTATION_COMMANDS)
    def test_mutation_triggers_osc(self, cmd):
        """Each mutating command sends at least one OSC message to SC."""
        mock_osc = MagicMock()
        mm = self._make_motion_manager(send_osc=mock_osc)

        from src.model.sequencer import MotionMode
        mm.set_mode(0, MotionMode.SEQ)
        mock_osc.reset_mock()

        seq = mm.get_seq_engine(0)
        seq.queue_command(cmd)
        seq.tick(0.001)

        osc_paths = {OSC_PATHS['step_set_rate'], OSC_PATHS['seq_set_play_mode'], OSC_PATHS['seq_set_bulk']}
        propagated = [c for c in mock_osc.call_args_list if c[0][0] in osc_paths]
        assert len(propagated) >= 1, \
            f"Command {cmd['type']} must trigger OSC propagation to SC"
