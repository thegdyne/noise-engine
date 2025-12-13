"""
Tests for value mapping functions in src/config
Tests map_value() and format_value() with edge cases
"""

import pytest
import math
from src.config import map_value, format_value, GENERATOR_PARAMS


class TestMapValueLinear:
    """Tests for linear curve mapping."""
    
    def test_linear_min(self):
        """Normalized 0 maps to min."""
        param = {'min': 10, 'max': 100, 'curve': 'lin'}
        assert map_value(0.0, param) == 10
    
    def test_linear_max(self):
        """Normalized 1 maps to max."""
        param = {'min': 10, 'max': 100, 'curve': 'lin'}
        assert map_value(1.0, param) == 100
    
    def test_linear_midpoint(self):
        """Normalized 0.5 maps to midpoint."""
        param = {'min': 0, 'max': 100, 'curve': 'lin'}
        assert map_value(0.5, param) == 50
    
    def test_linear_quarter(self):
        """Linear interpolation at 0.25."""
        param = {'min': 0, 'max': 100, 'curve': 'lin'}
        assert map_value(0.25, param) == 25


class TestMapValueExponential:
    """Tests for exponential curve mapping."""
    
    def test_exp_min(self):
        """Normalized 0 maps to min."""
        param = {'min': 20, 'max': 20000, 'curve': 'exp'}
        result = map_value(0.0, param)
        assert abs(result - 20) < 0.01
    
    def test_exp_max(self):
        """Normalized 1 maps to max."""
        param = {'min': 20, 'max': 20000, 'curve': 'exp'}
        result = map_value(1.0, param)
        assert abs(result - 20000) < 1
    
    def test_exp_midpoint_is_geometric_mean(self):
        """Normalized 0.5 maps to geometric mean for exp curve."""
        param = {'min': 100, 'max': 10000, 'curve': 'exp'}
        result = map_value(0.5, param)
        geometric_mean = math.sqrt(100 * 10000)  # 1000
        assert abs(result - geometric_mean) < 1
    
    def test_exp_protects_zero_min(self):
        """Exp curve handles min=0 gracefully."""
        param = {'min': 0, 'max': 1000, 'curve': 'exp'}
        # Should not crash, returns a valid number
        result = map_value(0.5, param)
        assert not math.isnan(result)
        assert not math.isinf(result)


class TestMapValueInversion:
    """Tests for inverted parameters (like resonance)."""
    
    def test_invert_swaps_direction(self):
        """Invert=True swaps high/low."""
        param = {'min': 0.001, 'max': 1.0, 'curve': 'lin', 'invert': True}
        # Slider up (1.0) should give LOW value (high resonance)
        high_slider = map_value(1.0, param)
        low_slider = map_value(0.0, param)
        assert high_slider < low_slider
    
    def test_invert_false_normal_direction(self):
        """Invert=False is normal direction."""
        param = {'min': 0, 'max': 100, 'curve': 'lin', 'invert': False}
        assert map_value(0.0, param) < map_value(1.0, param)
    
    def test_invert_missing_defaults_false(self):
        """Missing invert key defaults to False."""
        param = {'min': 0, 'max': 100, 'curve': 'lin'}
        assert map_value(0.0, param) < map_value(1.0, param)


class TestMapValueEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_clamps_below_zero(self):
        """Values below 0 are clamped."""
        param = {'min': 0, 'max': 100, 'curve': 'lin'}
        result = map_value(-0.5, param)
        assert result == 0  # Clamped to min
    
    def test_clamps_above_one(self):
        """Values above 1 are clamped."""
        param = {'min': 0, 'max': 100, 'curve': 'lin'}
        result = map_value(1.5, param)
        assert result == 100  # Clamped to max
    
    def test_handles_nan_input(self):
        """NaN input returns default."""
        param = {'min': 0, 'max': 100, 'curve': 'lin', 'default': 0.5}
        result = map_value(float('nan'), param)
        # NaN gets clamped to 0 or 1, not crash
        assert not math.isnan(result)
    
    def test_result_not_inf(self):
        """Result is never infinity."""
        param = {'min': 0.0001, 'max': 1e10, 'curve': 'exp'}
        result = map_value(1.0, param)
        assert not math.isinf(result)
    
    def test_result_within_bounds(self):
        """Result is clamped to reasonable bounds."""
        param = {'min': 0.0001, 'max': 1e35, 'curve': 'exp'}
        result = map_value(1.0, param)
        assert result <= 1e30  # Clamped per implementation


class TestMapValueWithRealParams:
    """Tests using actual GENERATOR_PARAMS definitions."""
    
    def test_frequency_range(self):
        """Frequency param maps to expected range."""
        freq_param = next(p for p in GENERATOR_PARAMS if p['key'] == 'frequency')
        
        low = map_value(0.0, freq_param)
        high = map_value(1.0, freq_param)
        
        assert low >= 20  # Audible range
        assert high <= 20000
        assert low < high
    
    def test_cutoff_range(self):
        """Cutoff param maps to expected range."""
        cutoff_param = next(p for p in GENERATOR_PARAMS if p['key'] == 'cutoff')
        
        low = map_value(0.0, cutoff_param)
        high = map_value(1.0, cutoff_param)
        
        assert low >= 1  # Nearly closed
        assert high <= 20000
    
    def test_resonance_inverted(self):
        """Resonance is inverted (high slider = low rq = more resonance)."""
        res_param = next(p for p in GENERATOR_PARAMS if p['key'] == 'resonance')
        
        slider_up = map_value(1.0, res_param)
        slider_down = map_value(0.0, res_param)
        
        # Inverted: up gives low value
        assert slider_up < slider_down
    
    def test_attack_decay_ranges(self):
        """Attack and decay have sensible time ranges."""
        attack_param = next(p for p in GENERATOR_PARAMS if p['key'] == 'attack')
        decay_param = next(p for p in GENERATOR_PARAMS if p['key'] == 'decay')
        
        # Attack should be short (under 1 second typically)
        attack_max = map_value(1.0, attack_param)
        assert attack_max <= 2.0  # seconds
        
        # Decay can be long (Maths-style)
        decay_max = map_value(1.0, decay_param)
        assert decay_max >= 1.0  # At least 1 second


class TestFormatValue:
    """Tests for format_value() display formatting."""
    
    def test_format_hz_low(self):
        """Low Hz values formatted correctly."""
        param = {'unit': 'Hz'}
        assert format_value(100, param) == "100Hz"
        assert format_value(999, param) == "999Hz"
    
    def test_format_hz_high(self):
        """High Hz values use kHz."""
        param = {'unit': 'Hz'}
        result = format_value(1000, param)
        assert 'kHz' in result
        assert format_value(5000, param) == "5.0kHz"
    
    def test_format_seconds_short(self):
        """Short times use ms."""
        param = {'unit': 's'}
        result = format_value(0.005, param)
        assert 'ms' in result
    
    def test_format_seconds_medium(self):
        """Medium times use ms without decimal."""
        param = {'unit': 's'}
        result = format_value(0.5, param)
        assert 'ms' in result
    
    def test_format_seconds_long(self):
        """Long times use seconds."""
        param = {'unit': 's'}
        result = format_value(2.5, param)
        assert 's' in result
        assert 'ms' not in result
    
    def test_format_no_unit(self):
        """No unit just formats number."""
        param = {'unit': ''}
        result = format_value(0.75, param)
        assert result == "0.75"
    
    def test_format_custom_unit(self):
        """Custom units are appended."""
        param = {'unit': 'dB'}
        result = format_value(6.0, param)
        assert 'dB' in result
