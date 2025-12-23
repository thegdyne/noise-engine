"""
tests/test_imaginarium_custom_params.py
Tests for Imaginarium custom parameter system per IMAGINARIUM_CUSTOM_PARAMS_SPEC.md

NOTE: This file imports base.py directly to avoid triggering method auto-registration.
"""

import math
import pytest
import importlib.util
import types
from pathlib import Path
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# =============================================================================
# Direct import of base.py (bypasses __init__.py auto-registration)
# =============================================================================
def _load_base_module():
    """Load base.py directly without triggering package __init__.py."""
    base_path = Path(__file__).parent.parent / "imaginarium" / "methods" / "base.py"
    spec = importlib.util.spec_from_file_location("base", base_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_base = _load_base_module()
ParamAxis = _base.ParamAxis
MacroControl = _base.MacroControl
MethodDefinition = _base.MethodDefinition
MethodTemplate = _base.MethodTemplate
_placeholder_custom_param = _base._placeholder_custom_param


# =============================================================================
# Phase 1: ParamAxis Extensions
# =============================================================================

class TestParamAxisNormalization:
    """Test normalize/denormalize round-trip (R7)."""
    
    def test_linear_normalize_min(self):
        """Linear: min value normalizes to 0."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin")
        assert axis.normalize(0.0) == pytest.approx(0.0)
    
    def test_linear_normalize_max(self):
        """Linear: max value normalizes to 1."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin")
        assert axis.normalize(100.0) == pytest.approx(1.0)
    
    def test_linear_normalize_mid(self):
        """Linear: mid value normalizes to 0.5."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin")
        assert axis.normalize(50.0) == pytest.approx(0.5)
    
    def test_linear_denormalize_min(self):
        """Linear: 0 denormalizes to min."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin")
        assert axis.denormalize(0.0) == pytest.approx(0.0)
    
    def test_linear_denormalize_max(self):
        """Linear: 1 denormalizes to max."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "lin")
        assert axis.denormalize(1.0) == pytest.approx(100.0)
    
    def test_linear_round_trip(self):
        """Linear: normalize -> denormalize round-trips."""
        axis = ParamAxis("test", 10.0, 90.0, 50.0, "lin")
        for value in [10.0, 25.0, 50.0, 75.0, 90.0]:
            norm = axis.normalize(value)
            denorm = axis.denormalize(norm)
            assert denorm == pytest.approx(value, abs=1e-6 * (90.0 - 10.0))
    
    def test_exp_normalize_min(self):
        """Exp: min value normalizes to 0."""
        axis = ParamAxis("test", 20.0, 8000.0, 400.0, "exp")
        assert axis.normalize(20.0) == pytest.approx(0.0)
    
    def test_exp_normalize_max(self):
        """Exp: max value normalizes to 1."""
        axis = ParamAxis("test", 20.0, 8000.0, 400.0, "exp")
        assert axis.normalize(8000.0) == pytest.approx(1.0)
    
    def test_exp_denormalize_min(self):
        """Exp: 0 denormalizes to min."""
        axis = ParamAxis("test", 20.0, 8000.0, 400.0, "exp")
        assert axis.denormalize(0.0) == pytest.approx(20.0)
    
    def test_exp_denormalize_max(self):
        """Exp: 1 denormalizes to max."""
        axis = ParamAxis("test", 20.0, 8000.0, 400.0, "exp")
        assert axis.denormalize(1.0) == pytest.approx(8000.0)
    
    def test_exp_round_trip(self):
        """Exp: normalize -> denormalize round-trips."""
        axis = ParamAxis("test", 20.0, 8000.0, 400.0, "exp")
        for value in [20.0, 100.0, 400.0, 2000.0, 8000.0]:
            norm = axis.normalize(value)
            denorm = axis.denormalize(norm)
            # Relative tolerance for exp
            assert denorm == pytest.approx(value, rel=1e-6)
    
    def test_normalize_clamps_below_min(self):
        """Values below min clamp to 0."""
        axis = ParamAxis("test", 10.0, 100.0, 50.0, "lin")
        assert axis.normalize(5.0) == pytest.approx(0.0)
    
    def test_normalize_clamps_above_max(self):
        """Values above max clamp to 1."""
        axis = ParamAxis("test", 10.0, 100.0, 50.0, "lin")
        assert axis.normalize(150.0) == pytest.approx(1.0)
    
    def test_denormalize_clamps_below_zero(self):
        """Norm below 0 clamps to min."""
        axis = ParamAxis("test", 10.0, 100.0, 50.0, "lin")
        assert axis.denormalize(-0.5) == pytest.approx(10.0)
    
    def test_denormalize_clamps_above_one(self):
        """Norm above 1 clamps to max."""
        axis = ParamAxis("test", 10.0, 100.0, 50.0, "lin")
        assert axis.denormalize(1.5) == pytest.approx(100.0)
    
    def test_exp_requires_positive_min(self):
        """Exp curve raises ValueError for non-positive min."""
        axis = ParamAxis("test", 0.0, 100.0, 50.0, "exp")
        with pytest.raises(ValueError, match="positive"):
            axis.normalize(50.0)
    
    def test_exp_requires_positive_max(self):
        """Exp curve raises ValueError for non-positive max."""
        axis = ParamAxis("test", 10.0, 0.0, 5.0, "exp")
        with pytest.raises(ValueError, match="positive"):
            axis.normalize(5.0)


class TestParamAxisToCustomParam:
    """Test to_custom_param JSON generation."""
    
    def test_basic_structure(self):
        """Generated dict has all required fields."""
        axis = ParamAxis(
            name="pulse_width",
            min_val=0.1,
            max_val=0.9,
            default=0.5,
            curve="lin",
            label="WID",
            tooltip="Pulse width",
            unit="",
        )
        result = axis.to_custom_param(0.5)
        
        assert "key" in result
        assert "label" in result
        assert "tooltip" in result
        assert "default" in result
        assert "min" in result
        assert "max" in result
        assert "curve" in result
        assert "unit" in result
    
    def test_key_is_axis_name(self):
        """R13: key equals axis.name."""
        axis = ParamAxis("my_param", 0.0, 1.0, 0.5, label="PAR")
        result = axis.to_custom_param(0.5)
        assert result["key"] == "my_param"
    
    def test_default_is_normalized(self):
        """R4: default is normalized version of baked value."""
        axis = ParamAxis("cutoff", 100.0, 8000.0, 1000.0, "exp", label="CUT")
        # Baked value 400 should normalize to something between 0 and 1
        result = axis.to_custom_param(400.0)
        assert 0.0 <= result["default"] <= 1.0
        # Verify round-trip
        assert axis.denormalize(result["default"]) == pytest.approx(400.0, rel=1e-6)
    
    def test_min_max_curve_fixed(self):
        """JSON always has min=0, max=1, curve=lin."""
        axis = ParamAxis("freq", 20.0, 8000.0, 440.0, "exp", label="FRQ")
        result = axis.to_custom_param(440.0)
        assert result["min"] == 0.0
        assert result["max"] == 1.0
        assert result["curve"] == "lin"
    
    def test_label_tooltip_unit_passed(self):
        """Metadata fields are passed through."""
        axis = ParamAxis(
            name="decay",
            min_val=0.01,
            max_val=10.0,
            default=1.0,
            curve="exp",
            label="DEC",
            tooltip="Decay time in seconds",
            unit="s",
        )
        result = axis.to_custom_param(1.0)
        assert result["label"] == "DEC"
        assert result["tooltip"] == "Decay time in seconds"
        assert result["unit"] == "s"


class TestParamAxisScReadExpr:
    """Test sc_read_expr marker and code generation."""
    
    def test_marker_present(self):
        """R12: Output contains marker token."""
        axis = ParamAxis("width", 0.1, 0.9, 0.5, "lin", label="WID")
        result = axis.sc_read_expr("customBus0", 0)
        assert "/// IMAG_CUSTOMBUS:0" in result
    
    def test_marker_index_varies(self):
        """Marker index matches axis_index argument."""
        axis = ParamAxis("test", 0.0, 1.0, 0.5, "lin", label="TST")
        result = axis.sc_read_expr("customBus3", 3)
        assert "/// IMAG_CUSTOMBUS:3" in result
    
    def test_linear_uses_linlin(self):
        """Linear curve uses linlin mapping."""
        axis = ParamAxis("width", 0.1, 0.9, 0.5, "lin", label="WID")
        result = axis.sc_read_expr("customBus0", 0)
        assert "linlin" in result
        assert "0.1" in result
        assert "0.9" in result
    
    def test_exp_uses_linexp(self):
        """Exp curve uses linexp mapping."""
        axis = ParamAxis("freq", 20.0, 8000.0, 440.0, "exp", label="FRQ")
        result = axis.sc_read_expr("customBus1", 1)
        assert "linexp" in result
        assert "20" in result
        assert "8000" in result
    
    def test_variable_assignment(self):
        """Output assigns to axis.name variable."""
        axis = ParamAxis("pulse_width", 0.1, 0.9, 0.5, "lin", label="WID")
        result = axis.sc_read_expr("customBus0", 0)
        assert "pulse_width =" in result


class TestPlaceholderCustomParam:
    """Test placeholder generation for unused slots."""
    
    def test_key_format(self):
        """Key is 'unused_N' where N is index."""
        result = _placeholder_custom_param(3)
        assert result["key"] == "unused_3"
    
    def test_label_is_dashes(self):
        """Label is '---'."""
        result = _placeholder_custom_param(0)
        assert result["label"] == "---"
    
    def test_tooltip_empty(self):
        """Tooltip is empty string."""
        result = _placeholder_custom_param(0)
        assert result["tooltip"] == ""
    
    def test_default_is_half(self):
        """Default is 0.5."""
        result = _placeholder_custom_param(0)
        assert result["default"] == 0.5
    
    def test_range_normalized(self):
        """min=0, max=1, curve=lin."""
        result = _placeholder_custom_param(0)
        assert result["min"] == 0.0
        assert result["max"] == 1.0
        assert result["curve"] == "lin"


# =============================================================================
# Phase 2: generate_json Tests
# =============================================================================

class MockMethodTemplate(MethodTemplate):
    """Concrete implementation for testing."""
    
    def __init__(self, axes: list):
        self._axes = axes
    
    @property
    def definition(self) -> MethodDefinition:
        return MethodDefinition(
            method_id="test/mock",
            family="test",
            display_name="Mock Method",
            template_version="1",
            param_axes=self._axes,
        )
    
    def generate_synthdef(self, synthdef_name: str, params: Dict, seed: int) -> str:
        return f"// Mock SynthDef {synthdef_name}"


class TestGenerateJson:
    """Test MethodTemplate.generate_json() custom_params handling."""
    
    def test_always_five_entries(self):
        """R3: custom_params always has exactly 5 entries."""
        # 0 axes
        method = MockMethodTemplate([])
        result = method.generate_json("Test", "test_synth")
        assert len(result["custom_params"]) == 5
        
        # 3 axes
        axes = [
            ParamAxis("a", 0.0, 1.0, 0.5, label="AAA"),
            ParamAxis("b", 0.0, 1.0, 0.5, label="BBB"),
            ParamAxis("c", 0.0, 1.0, 0.5, label="CCC"),
        ]
        method = MockMethodTemplate(axes)
        result = method.generate_json("Test", "test_synth")
        assert len(result["custom_params"]) == 5
        
        # 5 axes
        axes = [ParamAxis(f"p{i}", 0.0, 1.0, 0.5, label=f"P{i}X") for i in range(5)]
        method = MockMethodTemplate(axes)
        result = method.generate_json("Test", "test_synth")
        assert len(result["custom_params"]) == 5
        
        # 7 axes (only first 5 used)
        axes = [ParamAxis(f"p{i}", 0.0, 1.0, 0.5, label=f"P{i}X") for i in range(7)]
        method = MockMethodTemplate(axes)
        result = method.generate_json("Test", "test_synth")
        assert len(result["custom_params"]) == 5
    
    def test_placeholders_for_unused(self):
        """Unused slots have placeholder format."""
        axes = [
            ParamAxis("a", 0.0, 1.0, 0.5, label="AAA"),
            ParamAxis("b", 0.0, 1.0, 0.5, label="BBB"),
        ]
        method = MockMethodTemplate(axes)
        result = method.generate_json("Test", "test_synth")
        
        # First 2 are real
        assert result["custom_params"][0]["key"] == "a"
        assert result["custom_params"][1]["key"] == "b"
        
        # Remaining 3 are placeholders
        assert result["custom_params"][2]["key"] == "unused_2"
        assert result["custom_params"][3]["key"] == "unused_3"
        assert result["custom_params"][4]["key"] == "unused_4"
        
        # Check placeholder format
        for i in range(2, 5):
            p = result["custom_params"][i]
            assert p["label"] == "---"
            assert p["tooltip"] == ""
            assert p["default"] == 0.5
    
    def test_baked_params_used_for_defaults(self):
        """When params provided, they set defaults."""
        axes = [
            ParamAxis("cutoff", 100.0, 8000.0, 1000.0, "exp", label="CUT"),
        ]
        method = MockMethodTemplate(axes)
        
        # Pass baked value different from axis default
        result = method.generate_json("Test", "test_synth", params={"cutoff": 400.0})
        
        # Default should be normalized 400, not 1000
        default = result["custom_params"][0]["default"]
        denorm = axes[0].denormalize(default)
        assert denorm == pytest.approx(400.0, rel=1e-6)
    
    def test_missing_params_use_axis_default(self):
        """When params dict missing a key, use axis.default."""
        axes = [
            ParamAxis("a", 0.0, 100.0, 50.0, "lin", label="AAA"),
            ParamAxis("b", 0.0, 100.0, 75.0, "lin", label="BBB"),
        ]
        method = MockMethodTemplate(axes)
        
        # Only provide 'a'
        result = method.generate_json("Test", "test_synth", params={"a": 25.0})
        
        # 'a' uses provided value
        assert axes[0].denormalize(result["custom_params"][0]["default"]) == pytest.approx(25.0)
        # 'b' uses axis default (75.0)
        assert axes[1].denormalize(result["custom_params"][1]["default"]) == pytest.approx(75.0)
    
    def test_no_params_uses_all_defaults(self):
        """When params=None, all defaults from axes."""
        axes = [
            ParamAxis("a", 0.0, 100.0, 30.0, "lin", label="AAA"),
        ]
        method = MockMethodTemplate(axes)
        
        result = method.generate_json("Test", "test_synth", params=None)
        assert axes[0].denormalize(result["custom_params"][0]["default"]) == pytest.approx(30.0)
    
    def test_json_has_required_fields(self):
        """Output has name, synthdef, custom_params, output_trim_db."""
        method = MockMethodTemplate([])
        result = method.generate_json("Display Name", "synth_name")
        
        assert result["name"] == "Display Name"
        assert result["synthdef"] == "synth_name"
        assert "custom_params" in result
        assert "output_trim_db" in result


# =============================================================================
# Phase 3: dark_pulse Reference Implementation Tests
# =============================================================================

def _load_dark_pulse():
    """Load dark_pulse.py with base classes injected (avoids package __init__.py)."""
    # Read dark_pulse source
    dp_path = Path(__file__).parent.parent / "imaginarium" / "methods" / "subtractive" / "dark_pulse.py"
    source = dp_path.read_text()
    
    # Replace relative import with pass (we'll inject the classes)
    source = source.replace(
        '''from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)''',
        'pass  # imports injected by test loader'
    )
    
    # Create module with base classes pre-injected
    module = types.ModuleType("dark_pulse")
    module.MethodTemplate = MethodTemplate
    module.MethodDefinition = MethodDefinition
    module.ParamAxis = ParamAxis
    module.MacroControl = MacroControl
    module.Dict = Dict
    
    # Execute the modified source
    exec(compile(source, dp_path, 'exec'), module.__dict__)
    
    return module.DarkPulseTemplate()


class TestDarkPulseCustomParams:
    """Test dark_pulse reference implementation."""
    
    def test_all_axes_have_labels(self):
        """All param_axes have 3-char labels."""
        template = _load_dark_pulse()
        for axis in template.definition.param_axes:
            assert len(axis.label) == 3, f"{axis.name} label '{axis.label}' not 3 chars"
            assert axis.label.isupper() or axis.label.replace("0", "").replace("1", "").replace("2", "").isupper()
    
    def test_all_axes_have_tooltips(self):
        """All param_axes have non-empty tooltips."""
        template = _load_dark_pulse()
        for axis in template.definition.param_axes:
            assert axis.tooltip, f"{axis.name} has empty tooltip"
    
    def test_labels_unique(self):
        """All labels are unique within method."""
        template = _load_dark_pulse()
        labels = [a.label for a in template.definition.param_axes]
        assert len(labels) == len(set(labels)), f"Duplicate labels: {labels}"
    
    def test_synthdef_has_markers(self):
        """Generated SynthDef contains IMAG_CUSTOMBUS markers for all axes."""
        template = _load_dark_pulse()
        scd = template.generate_synthdef("test_synth", {}, 12345)
        
        # Should have markers 0-4 for 5 axes
        for i in range(5):
            assert f"/// IMAG_CUSTOMBUS:{i}" in scd, f"Missing marker {i}"
    
    def test_synthdef_no_baked_literals(self):
        """Generated SynthDef reads from buses, not baked literals."""
        template = _load_dark_pulse()
        scd = template.generate_synthdef("test_synth", {"pulse_width": 0.7}, 12345)
        
        # Should use In.kr(customBus*) not literal 0.7
        assert "In.kr(customBus0)" in scd
        assert "In.kr(customBus1)" in scd
        assert "In.kr(customBus2)" in scd
        assert "In.kr(customBus3)" in scd
        assert "In.kr(customBus4)" in scd
    
    def test_json_has_five_custom_params(self):
        """generate_json produces exactly 5 custom_params."""
        template = _load_dark_pulse()
        result = template.generate_json("Test", "test_synth", params={})
        assert len(result["custom_params"]) == 5
    
    def test_json_custom_params_have_labels(self):
        """All custom_params have proper labels."""
        template = _load_dark_pulse()
        result = template.generate_json("Test", "test_synth", params={})
        
        expected_labels = ["WID", "PWM", "RAT", "CUT", "RES"]
        actual_labels = [p["label"] for p in result["custom_params"]]
        assert actual_labels == expected_labels
    
    def test_json_defaults_match_baked(self):
        """JSON defaults are normalized versions of baked params."""
        template = _load_dark_pulse()
        axes = {a.name: a for a in template.definition.param_axes}
        
        baked = {"pulse_width": 0.3, "pwm_depth": 0.2, "cutoff_hz": 500.0}
        result = template.generate_json("Test", "test_synth", params=baked)
        
        # Check pulse_width
        pw_default = result["custom_params"][0]["default"]
        assert axes["pulse_width"].denormalize(pw_default) == pytest.approx(0.3, abs=0.01)
        
        # Check cutoff_hz (exp curve)
        cut_default = result["custom_params"][3]["default"]
        assert axes["cutoff_hz"].denormalize(cut_default) == pytest.approx(500.0, rel=0.01)
