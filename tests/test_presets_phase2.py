"""
Tests for Phase 2 preset expansion: BPM + Master section.
"""
import pytest
from src.presets.preset_schema import (
    MasterState,
    PresetState,
    validate_preset,
    PresetValidationError,
    NUM_SLOTS,
    BPM_MIN,
    BPM_MAX,
    BPM_DEFAULT,
    COMP_RATIOS,
    COMP_ATTACKS,
    COMP_RELEASES,
    COMP_SC_FREQS,
)


class TestMasterStatePhase2:
    """Test MasterState dataclass."""

    def test_default_values(self):
        """MasterState has correct defaults."""
        m = MasterState()
        assert m.volume == 0.8
        assert m.eq_hi == 120
        assert m.eq_mid == 120
        assert m.eq_lo == 120
        assert m.eq_hi_kill == 0
        assert m.eq_mid_kill == 0
        assert m.eq_lo_kill == 0
        assert m.eq_locut == 0
        assert m.eq_bypass == 0
        assert m.comp_threshold == 100
        assert m.comp_makeup == 0
        assert m.comp_ratio == 1
        assert m.comp_attack == 4
        assert m.comp_release == 4
        assert m.comp_sc == 0
        assert m.comp_bypass == 0
        assert m.limiter_ceiling == 590
        assert m.limiter_bypass == 0

    def test_to_dict(self):
        """to_dict includes all fields."""
        m = MasterState(
            volume=0.7,
            eq_hi=200,
            eq_mid=100,
            eq_lo=150,
            eq_hi_kill=1,
            eq_mid_kill=0,
            eq_lo_kill=1,
            eq_locut=1,
            eq_bypass=0,
            comp_threshold=200,
            comp_makeup=100,
            comp_ratio=2,
            comp_attack=3,
            comp_release=2,
            comp_sc=3,
            comp_bypass=1,
            limiter_ceiling=500,
            limiter_bypass=1,
        )
        d = m.to_dict()
        assert d["volume"] == 0.7
        assert d["eq_hi"] == 200
        assert d["eq_mid"] == 100
        assert d["eq_lo"] == 150
        assert d["eq_hi_kill"] == 1
        assert d["eq_mid_kill"] == 0
        assert d["eq_lo_kill"] == 1
        assert d["eq_locut"] == 1
        assert d["eq_bypass"] == 0
        assert d["comp_threshold"] == 200
        assert d["comp_makeup"] == 100
        assert d["comp_ratio"] == 2
        assert d["comp_attack"] == 3
        assert d["comp_release"] == 2
        assert d["comp_sc"] == 3
        assert d["comp_bypass"] == 1
        assert d["limiter_ceiling"] == 500
        assert d["limiter_bypass"] == 1

    def test_from_dict(self):
        """from_dict loads all fields."""
        d = {
            "volume": 0.6,
            "eq_hi": 180,
            "eq_mid": 90,
            "eq_lo": 140,
            "eq_hi_kill": 1,
            "eq_mid_kill": 1,
            "eq_lo_kill": 0,
            "eq_locut": 0,
            "eq_bypass": 1,
            "comp_threshold": 150,
            "comp_makeup": 50,
            "comp_ratio": 0,
            "comp_attack": 2,
            "comp_release": 3,
            "comp_sc": 4,
            "comp_bypass": 0,
            "limiter_ceiling": 400,
            "limiter_bypass": 0,
        }
        m = MasterState.from_dict(d)
        assert m.volume == 0.6
        assert m.eq_hi == 180
        assert m.eq_mid == 90
        assert m.eq_lo == 140
        assert m.eq_hi_kill == 1
        assert m.eq_mid_kill == 1
        assert m.eq_lo_kill == 0
        assert m.eq_locut == 0
        assert m.eq_bypass == 1
        assert m.comp_threshold == 150
        assert m.comp_makeup == 50
        assert m.comp_ratio == 0
        assert m.comp_attack == 2
        assert m.comp_release == 3
        assert m.comp_sc == 4
        assert m.comp_bypass == 0
        assert m.limiter_ceiling == 400
        assert m.limiter_bypass == 0

    def test_from_dict_defaults(self):
        """from_dict uses defaults for missing fields."""
        m = MasterState.from_dict({})
        assert m.volume == 0.8
        assert m.eq_hi == 120
        assert m.comp_ratio == 1
        assert m.limiter_ceiling == 590

    def test_round_trip(self):
        """to_dict -> from_dict preserves all values."""
        original = MasterState(
            volume=0.65,
            eq_hi=175,
            eq_mid=85,
            eq_lo=195,
            eq_hi_kill=1,
            eq_mid_kill=1,
            eq_lo_kill=1,
            eq_locut=1,
            eq_bypass=1,
            comp_threshold=250,
            comp_makeup=150,
            comp_ratio=2,
            comp_attack=5,
            comp_release=4,
            comp_sc=5,
            comp_bypass=1,
            limiter_ceiling=300,
            limiter_bypass=1,
        )
        restored = MasterState.from_dict(original.to_dict())
        assert restored.volume == original.volume
        assert restored.eq_hi == original.eq_hi
        assert restored.eq_mid == original.eq_mid
        assert restored.eq_lo == original.eq_lo
        assert restored.eq_hi_kill == original.eq_hi_kill
        assert restored.eq_mid_kill == original.eq_mid_kill
        assert restored.eq_lo_kill == original.eq_lo_kill
        assert restored.eq_locut == original.eq_locut
        assert restored.eq_bypass == original.eq_bypass
        assert restored.comp_threshold == original.comp_threshold
        assert restored.comp_makeup == original.comp_makeup
        assert restored.comp_ratio == original.comp_ratio
        assert restored.comp_attack == original.comp_attack
        assert restored.comp_release == original.comp_release
        assert restored.comp_sc == original.comp_sc
        assert restored.comp_bypass == original.comp_bypass
        assert restored.limiter_ceiling == original.limiter_ceiling
        assert restored.limiter_bypass == original.limiter_bypass


class TestPresetStateBPM:
    """Test BPM in PresetState."""

    def test_default_bpm(self):
        """PresetState has default BPM."""
        preset = PresetState()
        assert preset.bpm == BPM_DEFAULT

    def test_bpm_in_to_dict(self):
        """BPM included in to_dict."""
        preset = PresetState()
        preset.bpm = 140
        d = preset.to_dict()
        assert d["bpm"] == 140

    def test_bpm_from_dict(self):
        """BPM loaded from dict."""
        preset = PresetState.from_dict({"bpm": 160})
        assert preset.bpm == 160

    def test_bpm_default_when_missing(self):
        """BPM defaults when missing (v1 compat)."""
        preset = PresetState.from_dict({})
        assert preset.bpm == BPM_DEFAULT


class TestPresetStateMaster:
    """Test master section in PresetState."""

    def test_has_master(self):
        """PresetState has master field."""
        preset = PresetState()
        assert hasattr(preset, 'master')
        assert isinstance(preset.master, MasterState)

    def test_master_in_to_dict(self):
        """Master included in to_dict."""
        preset = PresetState()
        preset.master.eq_hi = 200
        preset.master.comp_ratio = 2
        d = preset.to_dict()
        assert d["master"]["eq_hi"] == 200
        assert d["master"]["comp_ratio"] == 2

    def test_master_from_dict(self):
        """Master loaded from dict."""
        preset = PresetState.from_dict({
            "master": {
                "volume": 0.5,
                "eq_lo": 100,
                "comp_threshold": 300,
            }
        })
        assert preset.master.volume == 0.5
        assert preset.master.eq_lo == 100
        assert preset.master.comp_threshold == 300

    def test_master_default_when_missing(self):
        """Master defaults when missing (v1 compat)."""
        preset = PresetState.from_dict({})
        assert preset.master.volume == 0.8
        assert preset.master.eq_hi == 120


class TestValidationPhase2:
    """Test validation of Phase 2 fields."""

    def test_valid_bpm(self):
        """BPM within range is valid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "bpm": 140,
        }
        valid, errors = validate_preset(data)
        assert valid, errors

    def test_invalid_bpm_too_low(self):
        """BPM below minimum is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "bpm": 10,
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("bpm" in e for e in errors)

    def test_invalid_bpm_too_high(self):
        """BPM above maximum is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "bpm": 400,
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("bpm" in e for e in errors)

    def test_valid_master_eq(self):
        """Master EQ values 0-240 are valid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "master": {"eq_hi": 0, "eq_mid": 120, "eq_lo": 240}
        }
        valid, errors = validate_preset(data)
        assert valid, errors

    def test_invalid_master_eq(self):
        """Master EQ > 240 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "master": {"eq_hi": 250}
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("eq_hi" in e and "250" in e for e in errors)

    def test_valid_comp_ratio(self):
        """Comp ratio 0-2 is valid."""
        for ratio in range(COMP_RATIOS):
            data = {
                "version": 2,
                "slots": [{}] * NUM_SLOTS,
                "master": {"comp_ratio": ratio}
            }
            valid, errors = validate_preset(data)
            assert valid, f"comp_ratio={ratio} should be valid: {errors}"

    def test_invalid_comp_ratio(self):
        """Comp ratio >= 3 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "master": {"comp_ratio": 5}
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("comp_ratio" in e for e in errors)

    def test_valid_comp_attack(self):
        """Comp attack 0-5 is valid."""
        for attack in range(COMP_ATTACKS):
            data = {
                "version": 2,
                "slots": [{}] * NUM_SLOTS,
                "master": {"comp_attack": attack}
            }
            valid, errors = validate_preset(data)
            assert valid, f"comp_attack={attack} should be valid: {errors}"

    def test_invalid_comp_attack(self):
        """Comp attack >= 6 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "master": {"comp_attack": 10}
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("comp_attack" in e for e in errors)

    def test_valid_comp_release(self):
        """Comp release 0-4 is valid."""
        for release in range(COMP_RELEASES):
            data = {
                "version": 2,
                "slots": [{}] * NUM_SLOTS,
                "master": {"comp_release": release}
            }
            valid, errors = validate_preset(data)
            assert valid, f"comp_release={release} should be valid: {errors}"

    def test_valid_limiter_ceiling(self):
        """Limiter ceiling 0-600 is valid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "master": {"limiter_ceiling": 300}
        }
        valid, errors = validate_preset(data)
        assert valid, errors

    def test_invalid_limiter_ceiling(self):
        """Limiter ceiling > 600 is invalid."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "master": {"limiter_ceiling": 700}
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("limiter_ceiling" in e for e in errors)

    def test_bypass_must_be_0_or_1(self):
        """Bypass values must be 0 or 1."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "master": {"eq_bypass": 2}
        }
        valid, errors = validate_preset(data)
        assert not valid
        assert any("eq_bypass" in e for e in errors)

    def test_strict_mode_raises(self):
        """Strict mode raises on invalid master values."""
        data = {
            "version": 2,
            "slots": [{}] * NUM_SLOTS,
            "master": {"comp_ratio": 99}
        }
        with pytest.raises(PresetValidationError):
            validate_preset(data, strict=True)


class TestFullRoundTripPhase2:
    """Test full round-trip with Phase 2 fields."""

    def test_full_round_trip(self):
        """Full preset round-trip preserves BPM and master data."""
        preset = PresetState()
        preset.bpm = 145
        preset.master.volume = 0.7
        preset.master.eq_hi = 180
        preset.master.eq_lo_kill = 1
        preset.master.comp_threshold = 250
        preset.master.comp_ratio = 2
        preset.master.comp_attack = 3
        preset.master.limiter_ceiling = 400
        preset.master.limiter_bypass = 1

        json_str = preset.to_json()
        restored = PresetState.from_json(json_str)

        assert restored.bpm == 145
        assert restored.master.volume == 0.7
        assert restored.master.eq_hi == 180
        assert restored.master.eq_lo_kill == 1
        assert restored.master.comp_threshold == 250
        assert restored.master.comp_ratio == 2
        assert restored.master.comp_attack == 3
        assert restored.master.limiter_ceiling == 400
        assert restored.master.limiter_bypass == 1
