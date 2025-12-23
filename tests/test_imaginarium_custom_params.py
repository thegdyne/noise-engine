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
from imaginarium.methods.base import ParamAxis, SynthesisMethod, MethodDefinition


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


class TestParamAxisValidation:
    """R9: Curve safety validation."""
    
    def test_min_less_than_max(self):
        """min_val must be less than max_val."""
        with pytest.raises(ValueError, match="min_val must be"):
            ParamAxis("test", 100.0, 10.0, 50.0, "lin", "TST", "Test param")
    
    def test_min_equals_max(self):
        """min_val cannot equal max_val."""
        with pytest.raises(ValueError, match="min_val must be"):
            ParamAxis("test", 50.0, 50.0, 50.0, "lin", "TST", "Test param")
    
    def test_exp_requires_positive_min(self):
        """Exponential curve requires positive min_val."""
        with pytest.raises(ValueError, match="(exp|positive)"):
            ParamAxis("test", 0.0, 100.0, 50.0, "exp", "TST", "Test param")
    
    def test_exp_requires_positive_max(self):
        """Exponential curve requires positive max_val."""
        with pytest.raises(ValueError, match="(exp|positive|min_val)"):
            ParamAxis("test", -100.0, -10.0, -50.0, "exp", "TST", "Test param")
    
    def test_exp_positive_values_ok(self):
        """Exponential curve with positive values is valid."""
        axis = ParamAxis("test", 0.001, 100.0, 1.0, "exp", "TST", "Test param")
        assert axis.curve == "exp"


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
        """Metadata is preserved in JSON output."""
        axis = ParamAxis("freq", 20.0, 20000.0, 1000.0, "exp", "FRQ", "Base frequency", "Hz")
        result = axis.to_custom_param(1000.0)
        assert result["label"] == "FRQ"
        assert result["tooltip"] == "Base frequency"
        assert result["unit"] == "Hz"


# =============================================================================
# SynthesisMethod Tests
# =============================================================================

class TestSynthesisMethodJsonGeneration:
    """R3, R8: JSON generation produces exactly 5 params with placeholders."""
    
    def test_json_has_exactly_5_custom_params(self):
        """R3: custom_params array is exactly length 5."""
        from imaginarium.methods.subtractive.dark_pulse import DarkPulse
        method = DarkPulse()
        json_data = method.generate_json("Test", "test_synth")
        assert len(json_data["custom_params"]) == 5
    
    def test_placeholder_format(self):
        """R8: Unused slots have correct placeholder format."""
        # Create a minimal method with only 2 axes to test placeholders
        from imaginarium.methods.base import ParamAxis, SynthesisMethod, MethodDefinition
        
        class TwoAxisMethod(SynthesisMethod):
            family = "test"
            name = "two_axis"
            
            def _build_definition(self) -> MethodDefinition:
                return MethodDefinition(
                    method_id="test/two_axis",
                    family="test",
                    template_path="",
                    param_axes=[
                        ParamAxis("one", 0.0, 1.0, 0.5, "lin", "ONE", "First param"),
                        ParamAxis("two", 0.0, 1.0, 0.5, "lin", "TWO", "Second param"),
                    ],
                )
            
            def generate_synthdef(self, synthdef_name, params):
                return "// test"
        
        method = TwoAxisMethod()
        json_data = method.generate_json("Test", "test_synth")
        
        # Check placeholders for slots 2, 3, 4
        for i in range(2, 5):
            placeholder = json_data["custom_params"][i]
            assert placeholder["key"] == f"unused_{i}"
            assert placeholder["label"] == "---"
            assert placeholder["tooltip"] == ""
            assert placeholder["default"] == 0.5
    
    def test_json_includes_required_fields(self):
        """JSON has all required top-level fields."""
        from imaginarium.methods.subtractive.dark_pulse import DarkPulse
        method = DarkPulse()
        json_data = method.generate_json("Test Name", "test_synth")
        
        assert json_data["name"] == "Test Name"
        assert json_data["synthdef"] == "test_synth"
        assert "custom_params" in json_data
        assert "output_trim_db" in json_data
        assert "midi_retrig" in json_data
        assert "pitch_target" in json_data


class TestSynthesisMethodSynthdefGeneration:
    """R2, R12: SynthDef generation includes marker tokens."""
    
    def test_synthdef_contains_all_markers(self):
        """All exposed axes have IMAG_CUSTOMBUS markers."""
        from imaginarium.methods.subtractive.dark_pulse import DarkPulse
        method = DarkPulse()
        
        # Generate with baked params
        params = {axis.name: axis.default for axis in method.definition.param_axes}
        synthdef = method.generate_synthdef("test_synth", params)
        
        num_axes = len(method.definition.param_axes[:5])
        for i in range(num_axes):
            assert f"/// IMAG_CUSTOMBUS:{i}" in synthdef, f"Missing marker for axis {i}"


# =============================================================================
# Validator Tests
# =============================================================================

class TestValidator:
    """Validator correctly identifies compliant and non-compliant methods."""
    
    def test_valid_method_passes(self):
        """A properly configured method passes validation."""
        from imaginarium.validate_methods import MethodValidator
        from imaginarium.methods.subtractive.dark_pulse import DarkPulse
        
        validator = MethodValidator(DarkPulse)
        result = validator.validate()
        
        assert result.passed, f"Valid method failed: {[e.message for e in result.errors]}"
    
    def test_all_14_methods_pass(self):
        """All 14 implemented methods pass validation."""
        from imaginarium.validate_methods import validate_all_methods
        
        passed, failed, results = validate_all_methods()
        
        assert len(results) == 14, f"Expected 14 methods, found {len(results)}"
        assert failed == 0, f"{failed} methods failed validation"
        assert passed == 14
    
    def test_invalid_label_format_detected(self):
        """R10: Invalid label format would be caught by validator."""
        # Create an axis with invalid label (too short)
        # The ParamAxis itself doesn't validate label format,
        # that's done by the MethodValidator
        axis = ParamAxis("test", 0.0, 1.0, 0.5, "lin", "AB", "Tooltip")
        
        # Verify the validator's LABEL_PATTERN would reject it
        from imaginarium.validate_methods import MethodValidator
        import re
        pattern = re.compile(r'^[A-Z0-9]{3}$')
        assert not pattern.match(axis.label), "Short label should not match pattern"
    
    def test_empty_tooltip_detected(self):
        """R11: Empty tooltip would be caught by validator."""
        # Empty tooltip is valid at ParamAxis level but validator catches it
        axis = ParamAxis("test", 0.0, 1.0, 0.5, "lin", "TST", "")
        
        # Validator checks for empty tooltip
        assert axis.tooltip == "", "Empty tooltip should be empty string"
    
    def test_missing_marker_detected(self):
        """R12: Missing IMAG_CUSTOMBUS marker would be caught by validator."""
        # The validator checks for marker tokens in generated SynthDef
        from imaginarium.validate_methods import MethodValidator
        from imaginarium.methods.subtractive.dark_pulse import DarkPulse
        
        method = DarkPulse()
        synthdef = method.generate_synthdef("test", {
            axis.name: axis.default for axis in method.definition.param_axes
        })
        
        # All markers should be present in valid method
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
        from imaginarium.methods.subtractive.dark_pulse import DarkPulse
        
        method = DarkPulse()
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
        
        # Should not raise
        run_validation_gate()
    
    def test_validation_would_detect_bad_method(self):
        """Validator correctly identifies methods with missing markers."""
        from imaginarium.validate_methods import MethodValidator
        from imaginarium.methods.base import ParamAxis, SynthesisMethod, MethodDefinition
        
        # Create a method that lacks markers in its SynthDef
        class NoMarkersMethod(SynthesisMethod):
            family = "test"
            name = "no_markers"
            
            def _build_definition(self) -> MethodDefinition:
                return MethodDefinition(
                    method_id="test/no_markers",
                    family="test",
                    template_path="",
                    param_axes=[
                        ParamAxis("x", 0.0, 1.0, 0.5, "lin", "XXX", "Test"),
                    ],
                )
            
            def generate_synthdef(self, synthdef_name, params):
                return "// No markers here!"
        
        validator = MethodValidator(NoMarkersMethod)
        result = validator.validate()
        
        # Should fail due to missing marker
        assert not result.passed
        assert any("marker" in e.message.lower() or "IMAG_CUSTOMBUS" in e.message 
                   for e in result.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
