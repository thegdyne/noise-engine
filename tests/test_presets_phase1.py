"""
Tests for Phase 1 preset expansion: channel strip state.
"""
import pytest
from src.presets.preset_schema import (
    ChannelState,
    MixerState,
    PresetState,
    validate_preset,
    PresetValidationError,
    NUM_SLOTS,
    GAIN_STAGES,
)


class TestChannelStatePhase1:
    """Test expanded ChannelState with EQ, gain, sends, cuts."""

    def test_default_values(self):
        """New fields have correct defaults."""
        ch = ChannelState()
        assert ch.eq_hi == 100
        assert ch.eq_mid == 100
        assert ch.eq_lo == 100
        assert ch.gain == 0
        assert ch.echo_send == 0
        assert ch.verb_send == 0
        assert ch.lo_cut is False
        assert ch.hi_cut is False

    def test_to_dict_includes_new_fields(self):
        """to_dict includes all Phase 1 fields."""
        ch = ChannelState(
            eq_hi=150,
            eq_mid=80,
            eq_lo=120,
            gain=2,
            echo_send=100,
            verb_send=50,
            lo_cut=True,
            hi_cut=False,
        )
        d = ch.to_dict()
        assert d["eq_hi"] == 150
        assert d["eq_mid"] == 80
        assert d["eq_lo"] == 120
        assert d["gain"] == 2
        assert d["echo_send"] == 100
        assert d["verb_send"] == 50
        assert d["lo_cut"] is True
        assert d["hi_cut"] is False

    def test_from_dict_loads_new_fields(self):
        """from_dict correctly loads Phase 1 fields."""
        d = {
            "volume": 0.7,
            "pan": 0.3,
            "mute": True,
            "solo": False,
            "eq_hi": 180,
            "eq_mid": 90,
            "eq_lo": 110,
            "gain": 1,
            "echo_send": 75,
            "verb_send": 25,
            "lo_cut": False,
            "hi_cut": True,
        }
        ch = ChannelState.from_dict(d)
        assert ch.eq_hi == 180
        assert ch.eq_mid == 90
        assert ch.eq_lo == 110
        assert ch.gain == 1
        assert ch.echo_send == 75
        assert ch.verb_send == 25
        assert ch.lo_cut is False
        assert ch.hi_cut is True

    def test_from_dict_uses_defaults_for_missing(self):
        """from_dict uses defaults when Phase 1 fields missing (v1 compat)."""
        d = {"volume": 0.5, "pan": 0.5}  # v1 style, no new fields
        ch = ChannelState.from_dict(d)
        assert ch.eq_hi == 100
        assert ch.eq_mid == 100
        assert ch.eq_lo == 100
        assert ch.gain == 0
        assert ch.echo_send == 0
        assert ch.verb_send == 0
        assert ch.lo_cut is False
        assert ch.hi_cut is False

    def test_round_trip(self):
        """to_dict -> from_dict preserves all values."""
        original = ChannelState(
            volume=0.65,
            pan=0.25,
            mute=True,
            solo=True,
            eq_hi=175,
            eq_mid=85,
            eq_lo=115,
            gain=2,
            echo_send=88,
            verb_send=44,
            lo_cut=True,
            hi_cut=True,
        )
        restored = ChannelState.from_dict(original.to_dict())
        assert restored.volume == original.volume
        assert restored.pan == original.pan
        assert restored.mute == original.mute
        assert restored.solo == original.solo
        assert restored.eq_hi == original.eq_hi
        assert restored.eq_mid == original.eq_mid
        assert restored.eq_lo == original.eq_lo
        assert restored.gain == original.gain
        assert restored.echo_send == original.echo_send
        assert restored.verb_send == original.verb_send
        assert restored.lo_cut == original.lo_cut
        assert restored.hi_cut == original.hi_cut


class TestMixerStatePhase1:
    """Test MixerState with expanded channels."""

    def test_channels_have_new_fields(self):
        """MixerState channels include Phase 1 fields."""
        mixer = MixerState()
        assert len(mixer.channels) == NUM_SLOTS
        for ch in mixer.channels:
            assert hasattr(ch, 'eq_hi')
            assert hasattr(ch, 'gain')
            assert hasattr(ch, 'echo_send')
            assert hasattr(ch, 'lo_cut')

    def test_to_dict_includes_channel_new_fields(self):
        """MixerState.to_dict includes Phase 1 channel fields."""
        mixer = MixerState()
        mixer.channels[0].eq_hi = 150
        mixer.channels[0].gain = 2
        d = mixer.to_dict()
        assert d["channels"][0]["eq_hi"] == 150
        assert d["channels"][0]["gain"] == 2


class TestValidationPhase1:
    """Test validation of Phase 1 fields."""

    def test_valid_eq_values(self):
        """EQ values 0-200 are valid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mixer": {
                "channels": [
                    {"eq_hi": 0, "eq_mid": 100, "eq_lo": 200}
                ] + [{}] * (NUM_SLOTS - 1)
            }
        }
        valid, errors = validate_preset(data)
        assert valid, errors

    def test_invalid_eq_values_too_high(self):
        """EQ values > 200 are invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mixer": {
                "channels": [{"eq_hi": 250}] + [{}] * (NUM_SLOTS - 1)
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("eq_hi" in e and "250" in e for e in errors)

    def test_invalid_eq_values_negative(self):
        """EQ values < 0 are invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mixer": {
                "channels": [{"eq_lo": -10}] + [{}] * (NUM_SLOTS - 1)
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("eq_lo" in e for e in errors)

    def test_valid_gain_values(self):
        """Gain values 0-2 are valid."""
        for gain in [0, 1, 2]:
            data = {
                "version": 2,
                "slots": [{}] * NUM_SLOTS,
                "mixer": {
                    "channels": [{"gain": gain}] + [{}] * (NUM_SLOTS - 1)
                }
            }
            valid, errors = validate_preset(data)
            assert valid, f"gain={gain} should be valid: {errors}"

    def test_invalid_gain_value(self):
        """Gain value 3 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mixer": {
                "channels": [{"gain": 3}] + [{}] * (NUM_SLOTS - 1)
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("gain" in e for e in errors)

    def test_valid_send_values(self):
        """Send values 0-200 are valid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mixer": {
                "channels": [
                    {"echo_send": 0, "verb_send": 200}
                ] + [{}] * (NUM_SLOTS - 1)
            }
        }
        valid, errors = validate_preset(data)
        assert valid, errors

    def test_invalid_send_value(self):
        """Send value > 200 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mixer": {
                "channels": [{"echo_send": 300}] + [{}] * (NUM_SLOTS - 1)
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("echo_send" in e for e in errors)

    def test_cut_must_be_bool(self):
        """lo_cut and hi_cut must be boolean."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mixer": {
                "channels": [{"lo_cut": 1}] + [{}] * (NUM_SLOTS - 1)
            }
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("lo_cut" in e and "bool" in e for e in errors)

    def test_strict_mode_raises(self):
        """Strict mode raises PresetValidationError."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mixer": {
                "channels": [{"eq_hi": 999}] + [{}] * (NUM_SLOTS - 1)
            }
        }
        with pytest.raises(PresetValidationError):
            validate_preset(data, strict=True)

    def test_coerce_integral_float(self):
        """Integral floats are coerced with warning."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "mixer": {
                "channels": [{"eq_hi": 100.0}] + [{}] * (NUM_SLOTS - 1)
            }
        }
        valid, messages = validate_preset(data)
        assert valid  # Should still be valid
        # May have a warning about coercion
        assert any("coerced" in m for m in messages) or len(messages) == 0


class TestPresetStatePhase1:
    """Test PresetState with Phase 1 expansion."""

    def test_version_is_2(self):
        """Preset version should be 2."""
        preset = PresetState()
        assert preset.version == 2

    def test_mapping_version_exists(self):
        """mapping_version field exists."""
        preset = PresetState()
        assert hasattr(preset, 'mapping_version')
        assert preset.mapping_version == 1

    def test_full_round_trip(self):
        """Full preset round-trip preserves Phase 1 channel data."""
        preset = PresetState()
        preset.mixer.channels[0].eq_hi = 180
        preset.mixer.channels[0].gain = 2
        preset.mixer.channels[0].echo_send = 75
        preset.mixer.channels[0].lo_cut = True
        preset.mixer.channels[3].eq_mid = 50
        preset.mixer.channels[3].verb_send = 100
        preset.mixer.channels[3].hi_cut = True

        json_str = preset.to_json()
        restored = PresetState.from_json(json_str)

        assert restored.mixer.channels[0].eq_hi == 180
        assert restored.mixer.channels[0].gain == 2
        assert restored.mixer.channels[0].echo_send == 75
        assert restored.mixer.channels[0].lo_cut is True
        assert restored.mixer.channels[3].eq_mid == 50
        assert restored.mixer.channels[3].verb_send == 100
        assert restored.mixer.channels[3].hi_cut is True
