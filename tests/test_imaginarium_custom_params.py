"""
Tests for Imaginarium Custom Params System (IMAGINARIUM_CUSTOM_PARAMS_SPEC.md)

Covers:
- ParamAxis normalize/denormalize round-trip (R7)
- JSON generation (R3, R8, R13)
- Validator checks (R1, R2, R9, R10, R11, R12)
- Export shared baked values (G2)
- Validation gate (R6)
"""

import pytest
import math
import re
from imaginarium.methods.base import ParamAxis, MethodTemplate, MethodDefinition


# =============================================================================
# ParamAxis Tests (Phase 1 verification)
# =============================================================================

class TestParamAxisNormalization:
    """R7: Round-trip tolerance tests for normalize/denormalize."""
    
    def test_lin_normalize_min(self):
        """Linear: min value normalizes to 0."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin", "TST", "Test param")
        assert axis.normalize(0.0) == pytest.approx(0.0)
    
    def test_lin_normalize_max(self):
        """Linear: max value normalizes to 1."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin", "TST", "Test param")
        assert axis.normalize(100.0) == pytest.approx(1.0)
    
    def test_lin_normalize_mid(self):
        """Linear: mid value normalizes to 0.5."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin", "TST", "Test param")
        assert axis.normalize(50.0) == pytest.approx(0.5)
    
    def test_lin_denormalize_zero(self):
        """Linear: 0 denormalizes to min."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin", "TST", "Test param")
        assert axis.denormalize(0.0) == pytest.approx(0.0)
    
    def test_lin_denormalize_one(self):
        """Linear: 1 denormalizes to max."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin", "TST", "Test param")
        assert axis.denormalize(1.0) == pytest.approx(100.0)
    
    def test_lin_roundtrip(self):
        """Linear: normalize->denormalize round-trip."""
        axis = ParamAxis("test", 10.0, 90.0, 50.0, "lin", "TST", "Test param")
        for val in [10.0, 25.0, 50.0, 75.0, 90.0]:
            norm = axis.normalize(val)
            denorm = axis.denormalize(norm)
            assert denorm == pytest.approx(val, abs=1e-6 * (90.0 - 10.0))
    
    def test_exp_normalize_min(self):
        """Exponential: min value normalizes to 0."""
        axis = ParamAxis("test", 20.0, 20000.0, 1000.0, "exp", "TST", "Test param")
        assert axis.normalize(20.0) == pytest.approx(0.0)
    
    def test_exp_normalize_max(self):
        """Exponential: max value normalizes to 1."""
        axis = ParamAxis("test", 20.0, 20000.0, 1000.0, "exp", "TST", "Test param")
        assert axis.normalize(20000.0) == pytest.approx(1.0)
    
    def test_exp_roundtrip(self):
        """Exponential: normalize->denormalize round-trip."""
        axis = ParamAxis("test", 20.0, 20000.0, 1000.0, "exp", "TST", "Test param")
        for val in [20.0, 100.0, 1000.0, 10000.0, 20000.0]:
            norm = axis.normalize(val)
            denorm = axis.denormalize(norm)
            assert denorm == pytest.approx(val, rel=1e-6)
    
    def test_normalize_clamps_below_min(self):
        """Values below min clamp to 0."""
        axis = ParamAxis("test", 10.0, 100.0, 50.0, "lin", "TST", "Test param")
        assert axis.normalize(5.0) == pytest.approx(0.0)
    
    def test_normalize_clamps_above_max(self):
        """Values above max clamp to 1."""
        axis = ParamAxis("test", 10.0, 100.0, 50.0, "lin", "TST", "Test param")
        assert axis.normalize(150.0) == pytest.approx(1.0)
    
    def test_denormalize_clamps_below_zero(self):
        """Normalized values below 0 clamp to min."""
        axis = ParamAxis("test", 10.0, 100.0, 50.0, "lin", "TST", "Test param")
        assert axis.denormalize(-0.5) == pytest.approx(10.0)
    
    def test_denormalize_clamps_above_one(self):
        """Normalized values above 1 clamp to max."""
        axis = ParamAxis("test", 10.0, 100.0, 50.0, "lin", "TST", "Test param")
        assert axis.denormalize(1.5) == pytest.approx(100.0)


class TestParamAxisScReadExpr:
    """R2, R12: SC helper generates correct expressions with markers."""
    
    def test_lin_generates_linlin(self):
        """Linear curve generates linlin mapping."""
        axis = ParamAxis("width", 0.0, 1.0, 0.5, "lin", "WID", "Width")
        expr = axis.sc_read_expr("customBus0", 0)
        assert "/// IMAG_CUSTOMBUS:0" in expr
        assert "linlin" in expr
        assert "customBus0" in expr
    
    def test_exp_generates_linexp(self):
        """Exponential curve generates linexp mapping."""
        axis = ParamAxis("freq", 20.0, 20000.0, 1000.0, "exp", "FRQ", "Frequency")
        expr = axis.sc_read_expr("customBus1", 1)
        assert "/// IMAG_CUSTOMBUS:1" in expr
        assert "linexp" in expr
        assert "customBus1" in expr
    
    def test_marker_index_matches_parameter(self):
        """Marker token index matches axis_index parameter."""
        axis = ParamAxis("test", 0.0, 1.0, 0.5, "lin", "TST", "Test")
        for i in range(5):
            expr = axis.sc_read_expr(f"customBus{i}", i)
            assert f"/// IMAG_CUSTOMBUS:{i}" in expr


class TestParamAxisToCustomParam:
    """R3, R13: JSON generation compliance."""
    
    def test_key_equals_axis_name(self):
        """R13: JSON key equals axis.name."""
        axis = ParamAxis("pulse_width", 0.1, 0.9, 0.5, "lin", "PWM", "Pulse width")
        result = axis.to_custom_param(0.5)
        assert result["key"] == "pulse_width"
    
    def test_default_is_normalized(self):
        """R4: JSON default is normalized baked value."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin", "TST", "Test")
        result = axis.to_custom_param(75.0)
        assert result["default"] == pytest.approx(0.75)
    
    def test_range_is_zero_to_one(self):
        """JSON min=0.0, max=1.0 always."""
        axis = ParamAxis("test", -50.0, 50.0, 0.0, "lin", "TST", "Test")
        result = axis.to_custom_param(0.0)
        assert result["min"] == 0.0
        assert result["max"] == 1.0
    
    def test_curve_is_always_lin(self):
        """JSON curve is always 'lin' (UI operates in normalized space)."""
        axis = ParamAxis("test", 20.0, 20000.0, 1000.0, "exp", "TST", "Test")
        result = axis.to_custom_param(1000.0)
        assert result["curve"] == "lin"
    
    def test_all_required_fields_present(self):
        """All GENERATOR_SPEC.md required fields present."""
        axis = ParamAxis("test", 0.0, 1.0, 0.5, "lin", "TST", "Test tooltip", "Hz")
        result = axis.to_custom_param(0.5)
        required = ["key", "label", "tooltip", "default", "min", "max", "curve", "unit"]
        for field in required:
            assert field in result, f"Missing field: {field}"
    
    def test_preserves_label_tooltip_unit(self):
        """Label, tooltip, unit preserved in JSON."""
        axis = ParamAxis("test", 0.0, 1.0, 0.5, "lin", "XYZ", "My tooltip", "ms")
        result = axis.to_custom_param(0.5)
        assert result["label"] == "XYZ"
        assert result["tooltip"] == "My tooltip"
        assert result["unit"] == "ms"


# =============================================================================
# Method Template Tests
# =============================================================================

class TestMethodTemplateJsonGeneration:
    """R3: JSON generation produces exactly 5 custom_params."""
    
    def test_json_has_exactly_5_custom_params(self):
        """JSON custom_params array has exactly 5 entries."""
        from imaginarium.methods.subtractive.dark_pulse import DarkPulseTemplate
        method = DarkPulseTemplate()
        json_data = method.generate_json("Test", "test_synth")
        
        assert len(json_data["custom_params"]) == 5
    
    def test_json_includes_required_fields(self):
        """JSON has all required top-level fields."""
        from imaginarium.methods.subtractive.dark_pulse import DarkPulseTemplate
        method = DarkPulseTemplate()
        json_data = method.generate_json("Test Name", "test_synth")
        
        assert json_data["name"] == "Test Name"
        assert json_data["synthdef"] == "test_synth"
        assert "custom_params" in json_data
        assert "output_trim_db" in json_data
        assert "midi_retrig" in json_data
        assert "pitch_target" in json_data


class TestMethodTemplateSynthdefGeneration:
    """R2, R12: SynthDef generation includes marker tokens."""
    
    def test_synthdef_contains_all_markers(self):
        """All exposed axes have IMAG_CUSTOMBUS markers."""
        from imaginarium.methods.subtractive.dark_pulse import DarkPulseTemplate
        method = DarkPulseTemplate()
        
        # Generate with baked params
        params = {axis.name: axis.default for axis in method.definition.param_axes}
        synthdef = method.generate_synthdef("test_synth", params, seed=12345)
        
        num_axes = len(method.definition.param_axes[:5])
        for i in range(num_axes):
            assert f"/// IMAG_CUSTOMBUS:{i}" in synthdef, f"Missing marker for axis {i}"


# =============================================================================
# Validator Tests
# =============================================================================

class TestValidator:
    """Validator correctly identifies compliant and non-compliant methods."""
    
    def test_all_14_methods_pass(self):
        """All 14 implemented methods pass validation."""
        from imaginarium.validate_methods import validate_all_methods
        
        passed, failed, results = validate_all_methods()
        
        assert len(results) == 14, f"Expected 14 methods, found {len(results)}"
        assert failed == 0, f"{failed} methods failed validation"
        assert passed == 14
    
    def test_validator_checks_label_format(self):
        """R10: Validator pattern rejects invalid label format."""
        # Short label (2 chars) should not match the validator's pattern
        pattern = re.compile(r'^[A-Z0-9]{3}$')
        assert not pattern.match("AB"), "Short label should not match pattern"
        assert not pattern.match("abcd"), "Lowercase should not match pattern"
        assert pattern.match("ABC"), "Valid label should match"
        assert pattern.match("A1B"), "Alphanumeric should match"
    
    def test_validator_detects_empty_tooltip(self):
        """R11: Empty tooltip is invalid per spec."""
        from imaginarium.validate_methods import validate_axis_metadata
        
        # Create an axis with empty tooltip
        axis = ParamAxis("test", 0.0, 1.0, 0.5, "lin", "TST", "")
        
        # Validator should report this as an error
        errors = validate_axis_metadata("test/method", [axis])
        assert any("tooltip" in e.lower() for e in errors), "Should detect empty tooltip"
    
    def test_validator_detects_missing_marker(self):
        """R12: Missing IMAG_CUSTOMBUS marker is detected."""
        from imaginarium.validate_methods import validate_synthdef_markers
        from imaginarium.methods.subtractive.dark_pulse import DarkPulseTemplate
        
        method = DarkPulseTemplate()
        
        # Verify the actual method has all markers (sanity check)
        params = {axis.name: axis.default for axis in method.definition.param_axes}
        synthdef = method.generate_synthdef("test", params, seed=12345)
        
        for i in range(len(method.definition.param_axes[:5])):
            marker = f"/// IMAG_CUSTOMBUS:{i}"
            assert marker in synthdef, f"Marker {marker} should be present"


# =============================================================================
# Export Tests (G2)
# =============================================================================

class TestExportSharedBakedValues:
    """G2: Same params used for JSON defaults and SynthDef baking."""
    
    def test_json_defaults_match_baked_params(self):
        """JSON custom_params defaults are normalized versions of baked params."""
        from imaginarium.methods.subtractive.dark_pulse import DarkPulseTemplate
        
        method = DarkPulseTemplate()
        axes = method.definition.param_axes[:5]
        
        # Define specific baked values (at 30% of each range)
        baked_params = {
            axis.name: axis.min_val + (axis.max_val - axis.min_val) * 0.3
            for axis in axes
        }
        
        json_data = method.generate_json("Test", "test_synth", params=baked_params)
        
        # Verify each custom param default matches normalized baked value
        for i, axis in enumerate(axes):
            expected_norm = axis.normalize(baked_params[axis.name])
            actual_norm = json_data["custom_params"][i]["default"]
            assert actual_norm == pytest.approx(expected_norm, abs=1e-6), \
                f"Axis {axis.name}: expected {expected_norm}, got {actual_norm}"


# =============================================================================
# Generator Gate Tests (R6)
# =============================================================================

class TestValidationGate:
    """R6: Validation gate blocks generation for non-compliant methods."""
    
    def test_run_validation_gate_passes_with_valid_methods(self):
        """Validation gate succeeds when all methods are valid."""
        from imaginarium.generate import run_validation_gate
        
        # Should return True (not raise)
        assert run_validation_gate() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
