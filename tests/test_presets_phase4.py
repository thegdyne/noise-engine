"""
Tests for Phase 4 preset expansion: Modulation routing.
"""
import pytest
from src.presets.preset_schema import (
    PresetState,
    validate_preset,
    PresetValidationError,
    NUM_SLOTS,
    NUM_MOD_BUSES,
    MOD_POLARITIES_ROUTING,
)


class TestPresetStateModRouting:
    """Test mod_routing in PresetState."""

    def test_has_mod_routing(self):
        """PresetState has mod_routing field."""
        preset = PresetState()
        assert hasattr(preset, 'mod_routing')
        assert isinstance(preset.mod_routing, dict)
        assert "connections" in preset.mod_routing

    def test_default_mod_routing_empty(self):
        """Default mod_routing has empty connections."""
        preset = PresetState()
        assert preset.mod_routing == {"connections": []}

    def test_mod_routing_in_to_dict(self):
        """mod_routing included in to_dict."""
        preset = PresetState()
        preset.mod_routing = {
            "connections": [
                {
                    "source_bus": 0,
                    "target_slot": 1,
                    "target_param": "cutoff",
                    "depth": 1.0,
                    "amount": 0.5,
                    "offset": 0.0,
                    "polarity": 0,
                    "invert": False,
                }
            ]
        }
        d = preset.to_dict()
        assert "mod_routing" in d
        assert len(d["mod_routing"]["connections"]) == 1
        assert d["mod_routing"]["connections"][0]["source_bus"] == 0
        assert d["mod_routing"]["connections"][0]["target_param"] == "cutoff"

    def test_mod_routing_from_dict(self):
        """mod_routing loaded from dict."""
        preset = PresetState.from_dict({
            "mod_routing": {
                "connections": [
                    {
                        "source_bus": 5,
                        "target_slot": 3,
                        "target_param": "frequency",
                        "amount": 0.8,
                    }
                ]
            }
        })
        assert len(preset.mod_routing["connections"]) == 1
        conn = preset.mod_routing["connections"][0]
        assert conn["source_bus"] == 5
        assert conn["target_slot"] == 3
        assert conn["target_param"] == "frequency"
        assert conn["amount"] == 0.8

    def test_mod_routing_default_when_missing(self):
        """mod_routing defaults when missing (v1 compat)."""
        preset = PresetState.from_dict({})
        assert preset.mod_routing == {"connections": []}


class TestValidationPhase4:
    """Test validation of Phase 4 fields."""

    def test_valid_connection(self):
        """Valid connection passes validation."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {
                        "source_bus": 0,
                        "target_slot": 1,
                        "target_param": "cutoff",
                        "depth": 1.0,
                        "amount": 0.5,
                        "offset": 0.0,
                        "polarity": 0,
                        "invert": False,
                    }
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert valid, errors

    def test_valid_multiple_connections(self):
        """Multiple connections pass validation."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 1, "target_param": "cutoff"},
                    {"source_bus": 4, "target_slot": 2, "target_param": "frequency"},
                    {"source_bus": 15, "target_slot": 8, "target_param": "resonance"},
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert valid, errors

    def test_empty_connections_valid(self):
        """Empty connections list is valid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {"connections": []}
        }
        valid, errors = validate_preset(data)
        assert valid, errors

    def test_invalid_source_bus_too_high(self):
        """source_bus >= 16 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 20, "target_slot": 1, "target_param": "cutoff"}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("source_bus" in e for e in errors)

    def test_invalid_source_bus_negative(self):
        """source_bus < 0 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": -1, "target_slot": 1, "target_param": "cutoff"}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("source_bus" in e for e in errors)

    def test_invalid_target_slot_too_high(self):
        """target_slot > 8 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 10, "target_param": "cutoff"}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("target_slot" in e for e in errors)

    def test_invalid_target_slot_zero(self):
        """target_slot = 0 is invalid (1-indexed)."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 0, "target_param": "cutoff"}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("target_slot" in e for e in errors)

    def test_missing_source_bus(self):
        """Missing source_bus is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"target_slot": 1, "target_param": "cutoff"}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("source_bus" in e and "required" in e for e in errors)

    def test_missing_target_slot(self):
        """Missing target_slot is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_param": "cutoff"}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("target_slot" in e and "required" in e for e in errors)

    def test_missing_target_param(self):
        """Missing target_param is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 1}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("target_param" in e and "required" in e for e in errors)

    def test_invalid_depth(self):
        """depth > 1.0 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 1, "target_param": "cutoff", "depth": 1.5}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("depth" in e for e in errors)

    def test_invalid_amount(self):
        """amount > 1.0 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 1, "target_param": "cutoff", "amount": 2.0}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("amount" in e for e in errors)

    def test_invalid_offset_too_high(self):
        """offset > 1.0 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 1, "target_param": "cutoff", "offset": 1.5}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("offset" in e for e in errors)

    def test_invalid_offset_too_low(self):
        """offset < -1.0 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 1, "target_param": "cutoff", "offset": -1.5}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("offset" in e for e in errors)

    def test_valid_offset_range(self):
        """offset -1 to +1 is valid."""
        for offset in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            data = {
                "version": 2,
                "slots": [{}] * NUM_SLOTS,
                "mod_routing": {
                    "connections": [
                        {"source_bus": 0, "target_slot": 1, "target_param": "cutoff", "offset": offset}
                    ]
                }
            }
            valid, errors = validate_preset(data)
            assert valid, f"offset={offset} should be valid: {errors}"

    def test_invalid_polarity(self):
        """polarity >= 3 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 1, "target_param": "cutoff", "polarity": 5}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("polarity" in e for e in errors)

    def test_valid_polarity_values(self):
        """polarity 0-2 is valid."""
        for polarity in range(MOD_POLARITIES_ROUTING):
            data = {
                "version": 2,
                "slots": [{}] * NUM_SLOTS,
                "mod_routing": {
                    "connections": [
                        {"source_bus": 0, "target_slot": 1, "target_param": "cutoff", "polarity": polarity}
                    ]
                }
            }
            valid, errors = validate_preset(data)
            assert valid, f"polarity={polarity} should be valid: {errors}"

    def test_invert_must_be_bool(self):
        """invert must be bool."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 0, "target_slot": 1, "target_param": "cutoff", "invert": 1}
                ]
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("invert" in e and "bool" in e for e in errors)

    def test_strict_mode_raises(self):
        """Strict mode raises on invalid connection."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mod_routing": {
                "connections": [
                    {"source_bus": 99, "target_slot": 1, "target_param": "cutoff"}
                ]
            }
        }
        with pytest.raises(PresetValidationError):
            validate_preset(data, strict=True)


class TestFullRoundTripPhase4:
    """Test full round-trip with Phase 4 fields."""

    def test_full_round_trip(self):
        """Full preset round-trip preserves mod_routing data."""
        preset = PresetState()
        preset.mod_routing = {
            "connections": [
                {
                    "source_bus": 0,
                    "target_slot": 1,
                    "target_param": "cutoff",
                    "depth": 1.0,
                    "amount": 0.75,
                    "offset": -0.25,
                    "polarity": 1,
                    "invert": True,
                },
                {
                    "source_bus": 8,
                    "target_slot": 5,
                    "target_param": "frequency",
                    "depth": 0.5,
                    "amount": 1.0,
                    "offset": 0.5,
                    "polarity": 2,
                    "invert": False,
                },
            ]
        }

        json_str = preset.to_json()
        restored = PresetState.from_json(json_str)

        assert len(restored.mod_routing["connections"]) == 2
        
        conn1 = restored.mod_routing["connections"][0]
        assert conn1["source_bus"] == 0
        assert conn1["target_slot"] == 1
        assert conn1["target_param"] == "cutoff"
        assert conn1["amount"] == 0.75
        assert conn1["offset"] == -0.25
        assert conn1["polarity"] == 1
        assert conn1["invert"] == True
        
        conn2 = restored.mod_routing["connections"][1]
        assert conn2["source_bus"] == 8
        assert conn2["target_slot"] == 5
        assert conn2["target_param"] == "frequency"
