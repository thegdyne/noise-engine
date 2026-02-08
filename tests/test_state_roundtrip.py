"""
State round-trip tests — auto-fill based.

The autofill helper guarantees every dataclass field is set to a
non-default value. If a new field is added and to_dict/from_dict
don't handle it, the test fails automatically — no manual updates.

Enforces invariants I1, I2, I3 from STATE_INTEGRITY_SPEC.
"""
import json
from dataclasses import fields

from src.presets.preset_schema import (
    SlotState, ChannelState, MasterState, PresetState,
    MixerState, _SLOT_PARAM_KEYS, validate_preset,
)
from tests.helpers.state_helpers import autofill_nondefaults, schema_keys


class TestSlotStateRoundTrip:
    """I1: SlotState field-by-field round-trip."""

    def test_all_fields_survive(self):
        """Every SlotState field round-trips through to_dict/from_dict."""
        original = autofill_nondefaults(SlotState)
        restored = SlotState.from_dict(original.to_dict())

        for f in fields(SlotState):
            orig_val = getattr(original, f.name)
            rest_val = getattr(restored, f.name)
            assert rest_val == orig_val, (
                f"SlotState.{f.name} didn't round-trip: "
                f"expected {orig_val!r}, got {rest_val!r}"
            )

    def test_to_dict_covers_all_schema_keys(self):
        """I2: to_dict() emits every schema field."""
        d = autofill_nondefaults(SlotState).to_dict()
        emitted = set(d.keys()) | set(d.get("params", {}).keys())
        expected = schema_keys(SlotState)
        missing = expected - emitted
        assert not missing, f"to_dict() missing keys: {missing}"

    def test_from_dict_ignores_unknown_keys(self):
        """from_dict ignores keys not in the dataclass."""
        data = SlotState().to_dict()
        data["totally_unknown_field"] = 999
        slot = SlotState.from_dict(data)
        assert not hasattr(slot, "totally_unknown_field") or \
            getattr(slot, "totally_unknown_field", None) is None


class TestChannelStateRoundTrip:
    """I1: ChannelState field-by-field round-trip."""

    def test_all_fields_survive(self):
        """Every ChannelState field round-trips through to_dict/from_dict."""
        original = autofill_nondefaults(ChannelState)
        restored = ChannelState.from_dict(original.to_dict())
        for f in fields(ChannelState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"ChannelState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        """I2: to_dict() emits every schema field."""
        d = autofill_nondefaults(ChannelState).to_dict()
        expected = schema_keys(ChannelState)
        missing = expected - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"

    def test_legacy_echo_verb_migration(self):
        """Backward compat: echo_send/verb_send migrate to fx1_send/fx2_send."""
        data = {"echo_send": 42, "verb_send": 84}
        ch = ChannelState.from_dict(data)
        assert ch.fx1_send == 42
        assert ch.fx2_send == 84

    def test_new_keys_take_precedence_over_legacy(self):
        """fx1_send takes precedence over echo_send if both present."""
        data = {"fx1_send": 100, "echo_send": 42}
        ch = ChannelState.from_dict(data)
        assert ch.fx1_send == 100


class TestMasterStateRoundTrip:
    """I1: MasterState field-by-field round-trip."""

    def test_all_fields_survive(self):
        """Every MasterState field round-trips through to_dict/from_dict."""
        original = autofill_nondefaults(MasterState)
        restored = MasterState.from_dict(original.to_dict())
        for f in fields(MasterState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"MasterState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        """I2: to_dict() emits every schema field."""
        d = autofill_nondefaults(MasterState).to_dict()
        expected = schema_keys(MasterState)
        missing = expected - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"


class TestPresetStateRoundTrip:
    """I3: Full PresetState round-trip through JSON."""

    def test_full_preset_round_trips(self):
        """Full PresetState with autofilled slot survives to_json/from_json."""
        state = PresetState(name="RoundTripTest", bpm=140)
        state.slots[0] = autofill_nondefaults(SlotState)
        state.mixer.channels[0] = autofill_nondefaults(ChannelState)

        restored = PresetState.from_json(state.to_json())

        for f in fields(SlotState):
            orig = getattr(state.slots[0], f.name)
            rest = getattr(restored.slots[0], f.name)
            assert rest == orig, f"PresetState.slots[0].{f.name} lost in round-trip"

        for f in fields(ChannelState):
            orig = getattr(state.mixer.channels[0], f.name)
            rest = getattr(restored.mixer.channels[0], f.name)
            assert rest == orig, f"PresetState.mixer.channels[0].{f.name} lost in round-trip"

    def test_json_is_valid(self):
        """to_json produces valid JSON that can be parsed."""
        state = PresetState(name="JSONTest")
        state.slots[0] = autofill_nondefaults(SlotState)
        json_str = state.to_json()
        data = json.loads(json_str)
        assert data["name"] == "JSONTest"


class TestBackwardCompatibility:
    """Old presets with missing new keys load without error."""

    def test_old_preset_missing_new_keys(self):
        """Old preset JSON without new fields loads, gets dataclass defaults."""
        old_data = {
            "version": 1,
            "name": "OldPreset",
            "slots": [
                {
                    "generator": "FM",
                    "params": {"frequency": 0.5},
                    "filter_type": 0,
                    "env_source": 0,
                    "clock_rate": 4,
                    "midi_channel": 1,
                }
            ],
            "mixer": {"channels": [], "master_volume": 0.8},
        }
        preset = PresetState.from_dict(old_data)
        slot = preset.slots[0]
        # New fields should have dataclass defaults, not crash
        assert slot.arp_enabled is False
        assert slot.euclid_enabled is False
        assert slot.analog_enabled == 0
        assert slot.seq_steps == []
        assert slot.rst_rate == 0

    def test_old_preset_missing_master_keys(self):
        """Old preset without Heat/Filter master keys loads with defaults."""
        old_data = {
            "volume": 0.7,
            "eq_hi": 120,
        }
        master = MasterState.from_dict(old_data)
        assert master.volume == 0.7
        assert master.eq_hi == 120
        # Missing keys get dataclass defaults
        assert master.heat_bypass == 1
        assert master.filter_bypass == 1
        assert master.sync_f1 == 0


class TestDeserializeValidateApply:
    """Invariant: deserialize -> validate -> apply. from_dict is not the final gate."""

    def test_from_dict_accepts_out_of_range_validate_rejects(self):
        """from_dict does NOT reject out-of-range values; validate_preset does."""
        # Construct a slot dict with out-of-range values
        data = SlotState().to_dict()
        data["filter_type"] = 999  # out of range
        data["params"]["frequency"] = 5.0  # out of range

        # from_dict accepts it (no coercion, no rejection)
        slot = SlotState.from_dict(data)
        assert slot.filter_type == 999
        assert slot.frequency == 5.0

        # validate_preset rejects it
        preset_data = PresetState().to_dict()
        preset_data["slots"][0] = data
        is_valid, errors = validate_preset(preset_data)
        assert not is_valid
        assert any("filter_type" in e for e in errors)
        assert any("frequency" in e for e in errors)
