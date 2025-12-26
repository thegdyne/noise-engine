"""
Tests for Phase 3 preset expansion: Modulation sources.
"""
import pytest
from src.presets.preset_schema import (
    ModSlotState,
    ModSourcesState,
    PresetState,
    validate_preset,
    PresetValidationError,
    NUM_SLOTS,
    NUM_MOD_SLOTS,
    NUM_MOD_OUTPUTS,
    MOD_WAVEFORMS,
    MOD_PHASES,
    MOD_POLARITIES,
)


class TestModSlotState:
    """Test ModSlotState dataclass."""

    def test_default_values(self):
        """ModSlotState has correct defaults."""
        s = ModSlotState()
        assert s.generator_name == "Empty"
        assert s.params == {}
        assert s.output_wave == [0, 0, 0, 0]
        assert s.output_phase == [0, 3, 5, 6]
        assert s.output_polarity == [0, 0, 0, 0]

    def test_to_dict(self):
        """to_dict includes all fields."""
        s = ModSlotState(
            generator_name="LFO",
            params={"rate": 0.5, "depth": 0.8},
            output_wave=[1, 2, 3, 0],
            output_phase=[0, 2, 4, 6],
            output_polarity=[0, 1, 0, 1],
        )
        d = s.to_dict()
        assert d["generator_name"] == "LFO"
        assert d["params"] == {"rate": 0.5, "depth": 0.8}
        assert d["output_wave"] == [1, 2, 3, 0]
        assert d["output_phase"] == [0, 2, 4, 6]
        assert d["output_polarity"] == [0, 1, 0, 1]

    def test_from_dict(self):
        """from_dict loads all fields."""
        d = {
            "generator_name": "Sloth",
            "params": {"rate": 0.3},
            "output_wave": [4, 3, 2, 1],
            "output_phase": [1, 2, 3, 4],
            "output_polarity": [1, 1, 1, 1],
        }
        s = ModSlotState.from_dict(d)
        assert s.generator_name == "Sloth"
        assert s.params == {"rate": 0.3}
        assert s.output_wave == [4, 3, 2, 1]
        assert s.output_phase == [1, 2, 3, 4]
        assert s.output_polarity == [1, 1, 1, 1]

    def test_from_dict_defaults(self):
        """from_dict uses defaults for missing fields."""
        s = ModSlotState.from_dict({})
        assert s.generator_name == "Empty"
        assert s.params == {}
        assert s.output_wave == [0, 0, 0, 0]

    def test_round_trip(self):
        """to_dict -> from_dict preserves all values."""
        original = ModSlotState(
            generator_name="LFO",
            params={"rate": 0.7, "depth": 0.9, "mode": 2},
            output_wave=[2, 2, 2, 2],
            output_phase=[7, 5, 3, 1],
            output_polarity=[1, 0, 1, 0],
        )
        restored = ModSlotState.from_dict(original.to_dict())
        assert restored.generator_name == original.generator_name
        assert restored.params == original.params
        assert restored.output_wave == original.output_wave
        assert restored.output_phase == original.output_phase
        assert restored.output_polarity == original.output_polarity

    def test_to_dict_creates_copies(self):
        """to_dict creates copies, not references."""
        s = ModSlotState(params={"rate": 0.5}, output_wave=[1, 2, 3, 4])
        d = s.to_dict()
        d["params"]["new_key"] = 999
        d["output_wave"][0] = 999
        assert "new_key" not in s.params
        assert s.output_wave[0] == 1


class TestModSourcesState:
    """Test ModSourcesState dataclass."""

    def test_default_has_4_slots(self):
        """ModSourcesState has 4 slots by default."""
        m = ModSourcesState()
        assert len(m.slots) == NUM_MOD_SLOTS
        for slot in m.slots:
            assert isinstance(slot, ModSlotState)

    def test_to_dict(self):
        """to_dict includes all slots."""
        m = ModSourcesState()
        m.slots[0].generator_name = "LFO"
        m.slots[1].generator_name = "Sloth"
        d = m.to_dict()
        assert len(d["slots"]) == NUM_MOD_SLOTS
        assert d["slots"][0]["generator_name"] == "LFO"
        assert d["slots"][1]["generator_name"] == "Sloth"

    def test_from_dict(self):
        """from_dict loads all slots."""
        d = {
            "slots": [
                {"generator_name": "LFO", "params": {"rate": 0.5}},
                {"generator_name": "Sloth"},
                {"generator_name": "Empty"},
                {"generator_name": "LFO"},
            ]
        }
        m = ModSourcesState.from_dict(d)
        assert len(m.slots) == NUM_MOD_SLOTS
        assert m.slots[0].generator_name == "LFO"
        assert m.slots[0].params == {"rate": 0.5}
        assert m.slots[1].generator_name == "Sloth"

    def test_from_dict_pads_missing_slots(self):
        """from_dict pads to 4 slots if fewer provided."""
        d = {"slots": [{"generator_name": "LFO"}]}
        m = ModSourcesState.from_dict(d)
        assert len(m.slots) == NUM_MOD_SLOTS
        assert m.slots[0].generator_name == "LFO"
        assert m.slots[1].generator_name == "Sloth"

    def test_round_trip(self):
        """Full round-trip preserves all values."""
        original = ModSourcesState()
        original.slots[0].generator_name = "LFO"
        original.slots[0].params = {"rate": 0.6}
        original.slots[0].output_wave = [3, 2, 1, 0]
        original.slots[2].generator_name = "Sloth"
        original.slots[2].output_polarity = [1, 1, 0, 0]

        restored = ModSourcesState.from_dict(original.to_dict())
        assert restored.slots[0].generator_name == "LFO"
        assert restored.slots[0].params == {"rate": 0.6}
        assert restored.slots[0].output_wave == [3, 2, 1, 0]
        assert restored.slots[2].generator_name == "Sloth"
        assert restored.slots[2].output_polarity == [1, 1, 0, 0]


class TestPresetStateModSources:
    """Test mod_sources in PresetState."""

    def test_has_mod_sources(self):
        """PresetState has mod_sources field."""
        preset = PresetState()
        assert hasattr(preset, 'mod_sources')
        assert isinstance(preset.mod_sources, ModSourcesState)

    def test_mod_sources_in_to_dict(self):
        """mod_sources included in to_dict."""
        preset = PresetState()
        preset.mod_sources.slots[0].generator_name = "LFO"
        preset.mod_sources.slots[0].params = {"rate": 0.75}
        d = preset.to_dict()
        assert "mod_sources" in d
        assert d["mod_sources"]["slots"][0]["generator_name"] == "LFO"
        assert d["mod_sources"]["slots"][0]["params"]["rate"] == 0.75

    def test_mod_sources_from_dict(self):
        """mod_sources loaded from dict."""
        preset = PresetState.from_dict({
            "mod_sources": {
                "slots": [
                    {"generator_name": "Sloth", "output_polarity": [1, 0, 1, 0]},
                    {},
                    {},
                    {},
                ]
            }
        })
        assert preset.mod_sources.slots[0].generator_name == "Sloth"
        assert preset.mod_sources.slots[0].output_polarity == [1, 0, 1, 0]

    def test_mod_sources_default_when_missing(self):
        """mod_sources defaults when missing (v1 compat)."""
        preset = PresetState.from_dict({})
        assert len(preset.mod_sources.slots) == NUM_MOD_SLOTS
        assert preset.mod_sources.slots[0].generator_name == "LFO"


class TestValidationPhase3:
    """Test validation of Phase 3 fields."""

    def test_valid_mod_sources(self):
        """Valid mod_sources passes validation."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_sources": {
                "slots": [
                    {"generator_name": "LFO", "output_wave": [0, 1, 2, 3]},
                    {},
                    {},
                    {},
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert valid, errors

    def test_invalid_output_wave_value(self):
        """output_wave value >= MOD_WAVEFORMS is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_sources": {
                "slots": [
                    {"output_wave": [10, 0, 0, 0]},  # 10 is invalid
                    {},
                    {},
                    {},
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("output_wave" in e for e in errors)

    def test_invalid_output_phase_value(self):
        """output_phase value >= MOD_PHASES is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_sources": {
                "slots": [
                    {"output_phase": [0, 0, 0, 20]},  # 20 is invalid
                    {},
                    {},
                    {},
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("output_phase" in e for e in errors)

    def test_invalid_output_polarity_value(self):
        """output_polarity value >= MOD_POLARITIES is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_sources": {
                "slots": [
                    {"output_polarity": [0, 0, 5, 0]},  # 5 is invalid
                    {},
                    {},
                    {},
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("output_polarity" in e for e in errors)

    def test_invalid_param_value(self):
        """param value > 1.0 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_sources": {
                "slots": [
                    {"params": {"rate": 1.5}},  # 1.5 is invalid
                    {},
                    {},
                    {},
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("rate" in e for e in errors)

    def test_wrong_output_length_strict(self):
        """Wrong output_wave length rejected in strict mode."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_sources": {
                "slots": [
                    {"output_wave": [0, 0]},  # Only 2 items
                    {},
                    {},
                    {},
                ]
            }
        }
        with pytest.raises(PresetValidationError):
            validate_preset(data, strict=True)

    def test_wrong_slots_count_strict(self):
        """Wrong mod_sources.slots count rejected in strict mode."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_sources": {
                "slots": [{}]  # Only 1 slot
            }
        }
        with pytest.raises(PresetValidationError):
            validate_preset(data, strict=True)

    def test_generator_name_must_be_string(self):
        """generator_name must be string."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_sources": {
                "slots": [
                    {"generator_name": 123},  # Not a string
                    {},
                    {},
                    {},
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("generator_name" in e for e in errors)


class TestFullRoundTripPhase3:
    """Test full round-trip with Phase 3 fields."""

    def test_full_round_trip(self):
        """Full preset round-trip preserves mod_sources data."""
        preset = PresetState()
        preset.mod_sources.slots[0].generator_name = "LFO"
        preset.mod_sources.slots[0].params = {"rate": 0.6, "depth": 0.8}
        preset.mod_sources.slots[0].output_wave = [1, 2, 3, 4]
        preset.mod_sources.slots[0].output_phase = [7, 6, 5, 4]
        preset.mod_sources.slots[0].output_polarity = [1, 0, 1, 0]
        
        preset.mod_sources.slots[2].generator_name = "Sloth"
        preset.mod_sources.slots[2].params = {"rate": 0.1}

        json_str = preset.to_json()
        restored = PresetState.from_json(json_str)

        assert restored.mod_sources.slots[0].generator_name == "LFO"
        assert restored.mod_sources.slots[0].params == {"rate": 0.6, "depth": 0.8}
        assert restored.mod_sources.slots[0].output_wave == [1, 2, 3, 4]
        assert restored.mod_sources.slots[0].output_phase == [7, 6, 5, 4]
        assert restored.mod_sources.slots[0].output_polarity == [1, 0, 1, 0]
        assert restored.mod_sources.slots[2].generator_name == "Sloth"
        assert restored.mod_sources.slots[2].params == {"rate": 0.1}
