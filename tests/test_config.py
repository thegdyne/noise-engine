"""
Tests for src/config/__init__.py
Validates constants, mappings, and configuration integrity
"""

import pytest
from src.config import (
    GENERATOR_PARAMS,
    CLOCK_RATES,
    CLOCK_RATE_INDEX,
    CLOCK_DEFAULT_INDEX,
    ENV_SOURCES,
    ENV_SOURCE_INDEX,
    FILTER_TYPES,
    FILTER_TYPE_INDEX,
    BPM_DEFAULT,
    BPM_MIN,
    BPM_MAX,
    GENERATOR_CYCLE,
    MAX_CUSTOM_PARAMS,
    OSC_HOST,
    OSC_SEND_PORT,
    OSC_RECEIVE_PORT,
    OSC_PATHS,
    SIZES,
    LFO_WAVEFORMS,
    LFO_WAVEFORM_INDEX,
)


class TestGeneratorParams:
    """Tests for GENERATOR_PARAMS structure."""
    
    def test_has_required_params(self):
        """All 5 standard params exist."""
        keys = [p['key'] for p in GENERATOR_PARAMS]
        assert 'frequency' in keys
        assert 'cutoff' in keys
        assert 'resonance' in keys
        assert 'attack' in keys
        assert 'decay' in keys
    
    def test_param_count(self):
        """Exactly 5 standard params."""
        assert len(GENERATOR_PARAMS) == 5
    
    def test_param_structure(self):
        """Each param has required fields."""
        required_fields = ['key', 'label', 'tooltip', 'default', 'min', 'max', 'curve', 'unit', 'invert']
        for param in GENERATOR_PARAMS:
            for field in required_fields:
                assert field in param, f"Param {param.get('key', '?')} missing '{field}'"
    
    def test_param_defaults_in_range(self):
        """Default values are within min/max."""
        for param in GENERATOR_PARAMS:
            default = param['default']
            # Default is normalized 0-1, not actual value
            assert 0.0 <= default <= 1.0, f"{param['key']} default {default} not in 0-1"
    
    def test_param_min_less_than_max(self):
        """Min < max for all params."""
        for param in GENERATOR_PARAMS:
            assert param['min'] < param['max'], f"{param['key']} min >= max"
    
    def test_curve_values_valid(self):
        """Curve is either 'lin' or 'exp'."""
        for param in GENERATOR_PARAMS:
            assert param['curve'] in ('lin', 'exp'), f"{param['key']} has invalid curve"
    
    def test_labels_are_short(self):
        """Labels are 3 chars (for UI)."""
        for param in GENERATOR_PARAMS:
            assert len(param['label']) <= 4, f"{param['key']} label too long"


class TestClockRates:
    """Tests for clock rate constants."""
    
    def test_clock_rates_count(self):
        """13 clock rates as documented."""
        assert len(CLOCK_RATES) == 13
    
    def test_clock_rates_order(self):
        """Rates go from slowest (/32) to fastest (x32)."""
        assert CLOCK_RATES[0] == "/32"
        assert CLOCK_RATES[-1] == "x32"
        assert "CLK" in CLOCK_RATES
    
    def test_clock_default_is_clk(self):
        """Default index points to CLK."""
        assert CLOCK_RATES[CLOCK_DEFAULT_INDEX] == "CLK"
    
    def test_clock_rate_index_consistency(self):
        """CLOCK_RATE_INDEX matches CLOCK_RATES."""
        for rate in CLOCK_RATES:
            assert rate in CLOCK_RATE_INDEX
            assert CLOCK_RATES[CLOCK_RATE_INDEX[rate]] == rate


class TestEnvSources:
    """Tests for envelope source constants."""
    
    def test_env_sources_count(self):
        """3 envelope sources: OFF, CLK, MIDI."""
        assert len(ENV_SOURCES) == 3
    
    def test_env_sources_order(self):
        """Order is OFF=0, CLK=1, MIDI=2."""
        assert ENV_SOURCES[0] == "OFF"
        assert ENV_SOURCES[1] == "CLK"
        assert ENV_SOURCES[2] == "MIDI"
    
    def test_env_source_index_consistency(self):
        """ENV_SOURCE_INDEX matches ENV_SOURCES."""
        assert ENV_SOURCE_INDEX["OFF"] == 0
        assert ENV_SOURCE_INDEX["CLK"] == 1
        assert ENV_SOURCE_INDEX["MIDI"] == 2


class TestFilterTypes:
    """Tests for filter type constants."""
    
    def test_filter_types_count(self):
        """3 filter types: LP, HP, BP."""
        assert len(FILTER_TYPES) == 3
    
    def test_filter_type_index_values(self):
        """Filter indices match SC convention."""
        assert FILTER_TYPE_INDEX["LP"] == 0
        assert FILTER_TYPE_INDEX["HP"] == 1
        assert FILTER_TYPE_INDEX["BP"] == 2


class TestBPM:
    """Tests for BPM constants."""
    
    def test_bpm_range_valid(self):
        """BPM range is sensible."""
        assert BPM_MIN < BPM_DEFAULT < BPM_MAX
        assert BPM_MIN >= 1  # Can't have 0 or negative BPM
        assert BPM_MAX <= 999  # Reasonable upper limit
    
    def test_bpm_default_reasonable(self):
        """Default BPM is standard tempo."""
        assert 60 <= BPM_DEFAULT <= 180


class TestGeneratorCycle:
    """Tests for generator cycle list."""
    
    def test_starts_with_empty(self):
        """First entry is Empty."""
        assert GENERATOR_CYCLE[0] == "Empty"
    
    def test_no_duplicates(self):
        """No duplicate generator names."""
        assert len(GENERATOR_CYCLE) == len(set(GENERATOR_CYCLE))
    
    def test_reasonable_count(self):
        """Has expected number of generators (22 + Empty)."""
        assert len(GENERATOR_CYCLE) >= 20  # At least 20 generators


class TestOSC:
    """Tests for OSC configuration."""
    
    def test_osc_host_is_localhost(self):
        """OSC host is localhost."""
        assert OSC_HOST == "127.0.0.1"
    
    def test_osc_ports_different(self):
        """Send and receive ports are different."""
        assert OSC_SEND_PORT != OSC_RECEIVE_PORT
    
    def test_osc_ports_valid(self):
        """Ports are in valid range."""
        assert 1024 <= OSC_SEND_PORT <= 65535
        assert 1024 <= OSC_RECEIVE_PORT <= 65535
    
    def test_osc_paths_not_empty(self):
        """OSC_PATHS has entries."""
        assert len(OSC_PATHS) > 0
    
    def test_osc_paths_start_with_slash(self):
        """All OSC paths start with /."""
        for key, path in OSC_PATHS.items():
            assert path.startswith('/'), f"OSC path '{key}' doesn't start with /"
    
    def test_osc_paths_noise_prefix(self):
        """All OSC paths use /noise/ prefix."""
        for key, path in OSC_PATHS.items():
            assert path.startswith('/noise/'), f"OSC path '{key}' missing /noise/ prefix"
    
    def test_required_osc_paths_exist(self):
        """Critical OSC paths are defined."""
        required = [
            'clock_bpm',
            'gen_frequency',
            'gen_cutoff',
            'gen_resonance',
            'gen_attack',
            'gen_decay',
            'gen_filter_type',
            'gen_env_source',
            'gen_clock_rate',
            'start_generator',
            'stop_generator',
            'ping',
            'pong',
            'heartbeat',
            'heartbeat_ack',
        ]
        for path_key in required:
            assert path_key in OSC_PATHS, f"Missing required OSC path: {path_key}"


class TestLFO:
    """Tests for LFO constants."""
    
    def test_lfo_waveforms_count(self):
        """4 LFO waveforms."""
        assert len(LFO_WAVEFORMS) == 4
    
    def test_lfo_waveform_index_consistency(self):
        """LFO_WAVEFORM_INDEX matches LFO_WAVEFORMS."""
        for wf in LFO_WAVEFORMS:
            assert wf in LFO_WAVEFORM_INDEX


class TestSizes:
    """Tests for UI size constants."""
    
    def test_sizes_not_empty(self):
        """SIZES has entries."""
        assert len(SIZES) > 0
    
    def test_sizes_are_positive(self):
        """All sizes are positive."""
        for key, value in SIZES.items():
            if isinstance(value, tuple):
                assert all(v > 0 for v in value), f"SIZES['{key}'] has non-positive value"
            else:
                assert value > 0, f"SIZES['{key}'] is not positive"


class TestMaxCustomParams:
    """Tests for custom params limit."""
    
    def test_max_custom_params_value(self):
        """MAX_CUSTOM_PARAMS is 5."""
        assert MAX_CUSTOM_PARAMS == 5
