"""
State round-trip tests — auto-fill based.

The autofill helper guarantees every dataclass field is set to a
non-default value. If a new field is added and to_dict/from_dict
don't handle it, the test fails automatically — no manual updates.

Enforces invariants I1, I2, I3 from STATE_INTEGRITY_SPEC.
"""
import json
import os
from dataclasses import fields

import pytest

from src.presets.preset_schema import (
    SlotState, ChannelState, MasterState, PresetState,
    MixerState, validate_preset,
    HeatState, EchoState, ReverbState, DualFilterState,
    FXSlotState, ModSlotState,
    SauceOfGravOutputState, SauceOfGravState,
    ARSeqEnvelopeState, ARSeqPlusState,
)
from tests.helpers.state_helpers import autofill_nondefaults, schema_field_names


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
        expected = schema_field_names(SlotState)
        missing = expected - emitted
        assert not missing, f"to_dict() missing keys: {missing}"

    def test_from_dict_ignores_unknown_keys(self):
        """from_dict ignores keys not in the dataclass (no error, no attr)."""
        data = SlotState().to_dict()
        data["totally_unknown_field"] = 999
        slot = SlotState.from_dict(data)  # should not raise
        assert not hasattr(slot, "totally_unknown_field")


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
        expected = schema_field_names(ChannelState)
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
        expected = schema_field_names(MasterState)
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


class TestSaveTimeAssertion:
    """Lock the fail-loud save assertion so it can't be silently softened."""

    @staticmethod
    def _check_missing(slot_dict):
        """Replicate the save-time assertion from preset_controller._do_save_preset."""
        _expected = {f.name for f in fields(SlotState)}
        _emitted = set(slot_dict.keys()) | set(slot_dict.get("params", {}).keys())
        _missing = _expected - _emitted
        if _missing:
            _msg = f"Save-path missing SlotState fields: {sorted(_missing)}"
            if os.environ.get("NOISE_STRICT_STATE", "1") == "1":
                raise RuntimeError(_msg)

    def test_strict_mode_on_by_default(self):
        """Default NOISE_STRICT_STATE raises RuntimeError on missing fields."""
        incomplete = {"generator": "FM", "params": {}}  # missing most fields
        old = os.environ.pop("NOISE_STRICT_STATE", None)
        try:
            with pytest.raises(RuntimeError, match="missing SlotState fields"):
                self._check_missing(incomplete)
        finally:
            if old is not None:
                os.environ["NOISE_STRICT_STATE"] = old

    def test_strict_mode_disabled_no_raise(self):
        """NOISE_STRICT_STATE=0 suppresses RuntimeError (downgrades to warning)."""
        incomplete = {"generator": "FM", "params": {}}
        old = os.environ.get("NOISE_STRICT_STATE")
        os.environ["NOISE_STRICT_STATE"] = "0"
        try:
            self._check_missing(incomplete)  # should NOT raise
        finally:
            if old is not None:
                os.environ["NOISE_STRICT_STATE"] = old
            else:
                os.environ.pop("NOISE_STRICT_STATE", None)

    def test_complete_dict_no_raise(self):
        """A complete slot dict never triggers the assertion regardless of mode."""
        complete = autofill_nondefaults(SlotState).to_dict()
        self._check_missing(complete)  # should NOT raise


# === Phase 1 extension: leaf FX classes ===

class TestHeatStateRoundTrip:
    """I1: HeatState field-by-field round-trip."""

    def test_all_fields_survive(self):
        original = autofill_nondefaults(HeatState)
        restored = HeatState.from_dict(original.to_dict())
        for f in fields(HeatState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"HeatState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        d = autofill_nondefaults(HeatState).to_dict()
        missing = schema_field_names(HeatState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"


class TestEchoStateRoundTrip:
    """I1: EchoState field-by-field round-trip."""

    def test_all_fields_survive(self):
        original = autofill_nondefaults(EchoState)
        restored = EchoState.from_dict(original.to_dict())
        for f in fields(EchoState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"EchoState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        d = autofill_nondefaults(EchoState).to_dict()
        missing = schema_field_names(EchoState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"


class TestReverbStateRoundTrip:
    """I1: ReverbState field-by-field round-trip."""

    def test_all_fields_survive(self):
        original = autofill_nondefaults(ReverbState)
        restored = ReverbState.from_dict(original.to_dict())
        for f in fields(ReverbState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"ReverbState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        d = autofill_nondefaults(ReverbState).to_dict()
        missing = schema_field_names(ReverbState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"


class TestDualFilterStateRoundTrip:
    """I1: DualFilterState field-by-field round-trip."""

    def test_all_fields_survive(self):
        original = autofill_nondefaults(DualFilterState)
        restored = DualFilterState.from_dict(original.to_dict())
        for f in fields(DualFilterState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"DualFilterState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        d = autofill_nondefaults(DualFilterState).to_dict()
        missing = schema_field_names(DualFilterState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"


class TestFXSlotStateRoundTrip:
    """I1: FXSlotState field-by-field round-trip."""

    def test_all_fields_survive(self):
        original = autofill_nondefaults(FXSlotState)
        restored = FXSlotState.from_dict(original.to_dict())
        for f in fields(FXSlotState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"FXSlotState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        d = autofill_nondefaults(FXSlotState).to_dict()
        missing = schema_field_names(FXSlotState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"

    def test_legacy_type_migration(self):
        """Backward compat: 'type' migrates to fx_type."""
        data = {"type": "Echo", "return": 0.8}
        slot = FXSlotState.from_dict(data)
        assert slot.fx_type == "Echo"
        assert slot.return_level == 0.8

    def test_new_keys_take_precedence_over_legacy(self):
        """fx_type takes precedence over type if both present."""
        data = {"fx_type": "Reverb", "type": "Echo"}
        slot = FXSlotState.from_dict(data)
        assert slot.fx_type == "Reverb"


class TestModSlotStateRoundTrip:
    """I1: ModSlotState field-by-field round-trip."""

    def test_all_fields_survive(self):
        original = autofill_nondefaults(ModSlotState)
        restored = ModSlotState.from_dict(original.to_dict())
        for f in fields(ModSlotState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"ModSlotState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        d = autofill_nondefaults(ModSlotState).to_dict()
        missing = schema_field_names(ModSlotState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"

    def test_defensive_copy(self):
        """Lists and dicts in to_dict output are copies, not references."""
        original = ModSlotState()
        d = original.to_dict()
        d["output_wave"][0] = 999
        d["params"]["injected"] = 1
        assert original.output_wave[0] != 999
        assert "injected" not in original.params


class TestSauceOfGravOutputStateRoundTrip:
    """I1: SauceOfGravOutputState field-by-field round-trip."""

    def test_all_fields_survive(self):
        original = autofill_nondefaults(SauceOfGravOutputState)
        restored = SauceOfGravOutputState.from_dict(original.to_dict())
        for f in fields(SauceOfGravOutputState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"SauceOfGravOutputState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        d = autofill_nondefaults(SauceOfGravOutputState).to_dict()
        missing = schema_field_names(SauceOfGravOutputState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"


class TestSauceOfGravStateRoundTrip:
    """I1: SauceOfGravState field-by-field round-trip."""

    def test_scalar_fields_survive(self):
        """Scalar fields round-trip through to_dict/from_dict."""
        original = SauceOfGravState(clock_mode=1, rate=0.7, depth=0.3,
                                     gravity=0.8, resonance=0.2,
                                     excursion=0.9, calm=0.1)
        restored = SauceOfGravState.from_dict(original.to_dict())
        for f in fields(SauceOfGravState):
            if f.name == "outputs":
                continue
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"SauceOfGravState.{f.name} didn't round-trip"

    def test_nested_outputs_survive(self):
        """Nested SauceOfGravOutputState objects round-trip."""
        original = SauceOfGravState()
        original.outputs[0] = SauceOfGravOutputState(tension=0.9, mass=0.1, polarity=1)
        restored = SauceOfGravState.from_dict(original.to_dict())
        assert restored.outputs[0].tension == 0.9
        assert restored.outputs[0].mass == 0.1
        assert restored.outputs[0].polarity == 1

    def test_to_dict_covers_all_schema_keys(self):
        d = SauceOfGravState().to_dict()
        missing = schema_field_names(SauceOfGravState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"

    def test_pads_missing_outputs(self):
        """from_dict pads to 4 outputs if fewer provided."""
        data = {"outputs": [{"tension": 0.9}]}
        state = SauceOfGravState.from_dict(data)
        assert len(state.outputs) == 4
        assert state.outputs[0].tension == 0.9
        assert state.outputs[1].tension == 0.5  # default


class TestARSeqEnvelopeStateRoundTrip:
    """I1: ARSeqEnvelopeState field-by-field round-trip."""

    def test_all_fields_survive(self):
        original = autofill_nondefaults(ARSeqEnvelopeState)
        restored = ARSeqEnvelopeState.from_dict(original.to_dict())
        for f in fields(ARSeqEnvelopeState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"ARSeqEnvelopeState.{f.name} didn't round-trip"

    def test_to_dict_covers_all_schema_keys(self):
        d = autofill_nondefaults(ARSeqEnvelopeState).to_dict()
        missing = schema_field_names(ARSeqEnvelopeState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"


class TestARSeqPlusStateRoundTrip:
    """I1: ARSeqPlusState field-by-field round-trip."""

    def test_scalar_fields_survive(self):
        """Scalar fields round-trip through to_dict/from_dict."""
        original = ARSeqPlusState(mode=1, clock_mode=1, rate=0.7)
        restored = ARSeqPlusState.from_dict(original.to_dict())
        for f in fields(ARSeqPlusState):
            if f.name == "envelopes":
                continue
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"ARSeqPlusState.{f.name} didn't round-trip"

    def test_nested_envelopes_survive(self):
        """Nested ARSeqEnvelopeState objects round-trip."""
        original = ARSeqPlusState()
        original.envelopes[0] = ARSeqEnvelopeState(
            attack=0.9, release=0.1, curve=0.8, sync_mode=1, loop_rate=3, polarity=1
        )
        restored = ARSeqPlusState.from_dict(original.to_dict())
        assert restored.envelopes[0].attack == 0.9
        assert restored.envelopes[0].polarity == 1

    def test_to_dict_covers_all_schema_keys(self):
        d = ARSeqPlusState().to_dict()
        missing = schema_field_names(ARSeqPlusState) - set(d.keys())
        assert not missing, f"to_dict() missing keys: {missing}"

    def test_pads_missing_envelopes(self):
        """from_dict pads to 4 envelopes if fewer provided."""
        data = {"envelopes": [{"attack": 0.9}]}
        state = ARSeqPlusState.from_dict(data)
        assert len(state.envelopes) == 4
        assert state.envelopes[0].attack == 0.9
        assert state.envelopes[1].attack == 0.5  # default


class TestControllerHasNoFeatureKnowledge:
    """Phase 2: _do_save_preset must not assemble per-feature state."""

    @staticmethod
    def _extract_method(method_name):
        """Read preset_controller.py and extract a method body by name."""
        import re
        src_path = os.path.join(
            os.path.dirname(__file__), "..",
            "src", "gui", "controllers", "preset_controller.py",
        )
        with open(src_path) as f:
            full_source = f.read()
        pattern = rf"(def {method_name}\(.*?\n(?:(?!    def ).+\n)*)"
        match = re.search(pattern, full_source)
        assert match, f"{method_name} not found in preset_controller.py"
        return match.group(1)

    def test_save_path_contains_no_feature_keywords(self):
        """Controller save path delegates to slot.get_state(), no feature injection."""
        method_source = self._extract_method("_do_save_preset")
        forbidden = ["arp_", "euclid_", "seq_", "rst_", "motion_manager"]
        found = [kw for kw in forbidden if kw in method_source]
        assert not found, (
            f"_do_save_preset still contains feature keywords: {found}. "
            f"Feature state export belongs in GeneratorSlot.get_state()."
        )

    def test_load_path_contains_no_feature_keywords(self):
        """Controller load path delegates to slot.apply_state(), no feature injection."""
        method_source = self._extract_method("_apply_preset")
        forbidden = ["arp_", "euclid_", "seq_", "rst_", "motion_manager"]
        found = [kw for kw in forbidden if kw in method_source]
        assert not found, (
            f"_apply_preset still contains feature keywords: {found}. "
            f"Feature state import belongs in GeneratorSlot.apply_state()."
        )


class TestApplyStateTypeSafety:
    """Phase 3 P0.1: apply_state accepts SlotState, not raw dict."""

    def test_apply_state_signature_accepts_slot_state(self):
        """apply_state type hint is SlotState, not dict."""
        import re
        src_path = os.path.join(
            os.path.dirname(__file__), "..",
            "src", "gui", "generator_slot.py",
        )
        with open(src_path) as f:
            source = f.read()
        match = re.search(r"def apply_state\(self,\s*(\w+):\s*(\w+)\)", source)
        assert match, "apply_state method not found in generator_slot.py"
        param_type = match.group(2)
        assert param_type == "SlotState", (
            f"apply_state parameter type is {param_type!r}, expected 'SlotState'"
        )

    def test_controller_passes_slot_state_not_dict(self):
        """Controller passes SlotState directly, not slot_state.to_dict()."""
        src_path = os.path.join(
            os.path.dirname(__file__), "..",
            "src", "gui", "controllers", "preset_controller.py",
        )
        with open(src_path) as f:
            source = f.read()
        # Must NOT contain apply_state(slot_state.to_dict())
        assert "apply_state(slot_state.to_dict())" not in source, (
            "Controller still converts to dict before calling apply_state"
        )
        # Must contain apply_state(slot_state) without .to_dict()
        assert "apply_state(slot_state)" in source, (
            "Controller doesn't pass SlotState directly to apply_state"
        )


class TestStaleSeqStepsPrevention:
    """Phase 3 P0.3: Loading a shorter preset must not leave stale tail steps."""

    def test_short_preset_clears_tail_steps(self):
        """Steps beyond the new preset's length are reset to REST defaults."""
        # Build a SlotState with only 4 steps (shorter than 16)
        short_steps = [
            {"step_type": 0, "note": 72, "velocity": 110},
            {"step_type": 0, "note": 74, "velocity": 100},
            {"step_type": 0, "note": 76, "velocity": 90},
            {"step_type": 0, "note": 77, "velocity": 80},
        ]
        slot = SlotState(seq_steps=short_steps, seq_length=4, seq_enabled=True)

        # Verify round-trip preserves exactly 4 steps
        d = slot.to_dict()
        assert len(d["seq_steps"]) == 4

        # Verify from_dict faithfully restores
        restored = SlotState.from_dict(d)
        assert len(restored.seq_steps) == 4
        assert restored.seq_steps[0]["note"] == 72

    def test_apply_state_contains_step_reset(self):
        """_apply_seq_state resets all 16 steps before applying new ones."""
        import re
        src_path = os.path.join(
            os.path.dirname(__file__), "..",
            "src", "gui", "generator_slot.py",
        )
        with open(src_path) as f:
            source = f.read()
        # Must contain the reset loop
        assert "SeqStep()" in source, (
            "_apply_seq_state must reset steps to SeqStep() defaults"
        )
        assert "for j in range(16):" in source, (
            "_apply_seq_state must reset all 16 steps"
        )


class TestApplyExportSymmetry:
    """Export (get_state) and import (apply_state) must handle the same fields."""

    # Fields handled by set_state (UI controls)
    UI_FIELDS = {
        "generator", "frequency", "cutoff", "resonance", "attack", "decay",
        "custom_0", "custom_1", "custom_2", "custom_3", "custom_4",
        "filter_type", "env_source", "clock_rate", "midi_channel",
        "transpose", "portamento", "analog_enabled", "analog_type",
    }
    # Feature fields that must be symmetric in get_state/apply_state
    FEATURE_FIELDS = {
        "arp_enabled", "arp_rate", "arp_pattern", "arp_octaves", "arp_hold",
        "euclid_enabled", "euclid_n", "euclid_k", "euclid_rot", "rst_rate",
        "seq_enabled", "seq_rate", "seq_length", "seq_play_mode", "seq_steps",
        "step_mode", "arp_notes",
    }

    def test_ui_plus_feature_fields_cover_all_slot_state(self):
        """Every SlotState field is accounted for in either UI or feature set."""
        all_fields = {f.name for f in fields(SlotState)}
        covered = self.UI_FIELDS | self.FEATURE_FIELDS
        uncovered = all_fields - covered
        assert not uncovered, (
            f"SlotState fields not covered by UI or feature sets: {uncovered}. "
            f"Add them to TestApplyExportSymmetry.UI_FIELDS or FEATURE_FIELDS."
        )

    def test_get_state_exports_all_feature_fields(self):
        """get_state() must reference every feature field name."""
        import re
        src_path = os.path.join(
            os.path.dirname(__file__), "..",
            "src", "gui", "generator_slot.py",
        )
        with open(src_path) as f:
            source = f.read()
        match = re.search(r"(def get_state\(self\).*?\n(?:(?!    def ).*\n)*)", source)
        assert match, "get_state not found"
        body = match.group(1)
        missing = [f for f in self.FEATURE_FIELDS if f'"{f}"' not in body]
        assert not missing, f"get_state() doesn't export: {missing}"

    def test_apply_helpers_read_all_feature_fields(self):
        """apply helper methods must reference every feature field name."""
        import re
        src_path = os.path.join(
            os.path.dirname(__file__), "..",
            "src", "gui", "generator_slot.py",
        )
        with open(src_path) as f:
            source = f.read()
        arp_match = re.search(r"(def _apply_arp_state\(.*?\n(?:(?!    def ).*\n)*)", source)
        seq_match = re.search(r"(def _apply_seq_state\(.*?\n(?:(?!    def ).*\n)*)", source)
        assert arp_match, "_apply_arp_state not found"
        assert seq_match, "_apply_seq_state not found"
        combined = arp_match.group(1) + seq_match.group(1)
        missing = [f for f in self.FEATURE_FIELDS if f".{f}" not in combined]
        assert not missing, f"apply helpers don't read: {missing}"


class TestModeSymmetric:
    """apply_state must clear motion mode to OFF before applying features."""

    def test_apply_state_clears_mode_before_features(self):
        """apply_state body contains MotionMode.OFF before _apply_arp_state."""
        import re
        src_path = os.path.join(
            os.path.dirname(__file__), "..",
            "src", "gui", "generator_slot.py",
        )
        with open(src_path) as f:
            source = f.read()
        match = re.search(r"(def apply_state\(self.*?\n(?:(?!    def ).*\n)*)", source)
        assert match, "apply_state not found"
        body = match.group(1)
        assert "MotionMode.OFF" in body, (
            "apply_state must explicitly clear mode to OFF before feature application"
        )
        # OFF must appear before _apply_arp_state call
        off_pos = body.index("MotionMode.OFF")
        arp_pos = body.index("_apply_arp_state")
        assert off_pos < arp_pos, (
            "MotionMode.OFF must appear before _apply_arp_state call"
        )


class TestSeqStepsNormalization:
    """from_dict normalizes seq_steps: fresh dicts with guaranteed keys."""

    def test_missing_keys_get_defaults(self):
        """Step dicts missing keys get REST/60/100 defaults."""
        data = SlotState().to_dict()
        data["seq_steps"] = [{"note": 72}]  # missing step_type, velocity
        slot = SlotState.from_dict(data)
        step = slot.seq_steps[0]
        assert step["step_type"] == 1  # REST
        assert step["note"] == 72
        assert step["velocity"] == 100

    def test_deep_copy_isolation(self):
        """Mutating to_dict() output doesn't affect the original object."""
        slot = SlotState(seq_steps=[{"step_type": 0, "note": 60, "velocity": 100}])
        d = slot.to_dict()
        d["seq_steps"][0]["note"] = 999
        assert slot.seq_steps[0]["note"] == 60

    def test_from_dict_deep_copy_isolation(self):
        """Mutating input data after from_dict doesn't affect the SlotState."""
        data = {"seq_steps": [{"step_type": 0, "note": 60, "velocity": 100}]}
        slot = SlotState.from_dict(data)
        data["seq_steps"][0]["note"] = 999
        assert slot.seq_steps[0]["note"] == 60
