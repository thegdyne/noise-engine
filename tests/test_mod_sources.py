"""
Tests for mod sources configuration
"""

import pytest
from src.config import (
    MOD_SLOT_COUNT,
    MOD_OUTPUTS_PER_SLOT,
    MOD_BUS_COUNT,
    MOD_GENERATOR_CYCLE,
    MOD_LFO_WAVEFORMS,
    MOD_LFO_PHASES,
    MOD_SLOTH_MODES,
    MOD_CLOCK_RATES,
    MOD_POLARITY,
    MOD_OUTPUT_LABELS,
    get_mod_generator_synthdef,
    get_mod_generator_custom_params,
    get_mod_generator_output_config,
    get_mod_output_labels,
)


class TestModConstants:
    """Test mod source constants."""
    
    def test_slot_count(self):
        """Should have 4 mod slots."""
        assert MOD_SLOT_COUNT == 4
        
    def test_outputs_per_slot(self):
        """Should have 4 outputs per slot (quadrature)."""
        assert MOD_OUTPUTS_PER_SLOT == 4
        
    def test_bus_count_ssot(self):
        """Bus count should equal slots x outputs (SSOT)."""
        assert MOD_BUS_COUNT == MOD_SLOT_COUNT * MOD_OUTPUTS_PER_SLOT
        assert MOD_BUS_COUNT == 16
        
    def test_generator_cycle(self):
        """Generator cycle should start with Empty."""
        assert MOD_GENERATOR_CYCLE[0] == "Empty"
        assert "LFO" in MOD_GENERATOR_CYCLE
        assert "Sloth" in MOD_GENERATOR_CYCLE
        
    def test_lfo_waveforms(self):
        """LFO should have 8 waveforms."""
        assert len(MOD_LFO_WAVEFORMS) == 8
        assert "Sin" in MOD_LFO_WAVEFORMS
        assert "Sqr" in MOD_LFO_WAVEFORMS
        
    def test_lfo_phases(self):
        """LFO phases should be 0-315 in 45 degree steps."""
        assert MOD_LFO_PHASES == [0, 45, 90, 135, 180, 225, 270, 315]
        assert len(MOD_LFO_PHASES) == 8
        
    def test_sloth_modes(self):
        """Sloth should have 3 modes."""
        assert len(MOD_SLOTH_MODES) == 3
        assert "Torpor" in MOD_SLOTH_MODES
        
    def test_clock_rates(self):
        """Clock rates should include divisions and multipliers."""
        assert "/4" in MOD_CLOCK_RATES
        assert "CLK" in MOD_CLOCK_RATES  # Base tempo (was "1")
        assert "x4" in MOD_CLOCK_RATES
        assert len(MOD_CLOCK_RATES) == 13  # 13 rates after clock unification
        
    def test_polarity(self):
        """Polarity should be NORM and INV (invert)."""
        assert MOD_POLARITY == ["NORM", "INV"]
        
    def test_output_labels(self):
        """Output labels should differ by generator type."""
        assert MOD_OUTPUT_LABELS["LFO"] == ["A", "B", "C", "D"]
        assert MOD_OUTPUT_LABELS["Sloth"] == ["X", "Y", "Z", "R"]
        assert MOD_OUTPUT_LABELS["Empty"] == ["A", "B", "C", "D"]


class TestModBusIndex:
    """Test bus index calculation."""
    
    def test_bus_index_formula(self):
        """Bus index = (slot - 1) * 4 + output."""
        # Slot 1, outputs 0-3 -> buses 0-3
        assert (1 - 1) * 4 + 0 == 0
        assert (1 - 1) * 4 + 1 == 1
        assert (1 - 1) * 4 + 2 == 2
        assert (1 - 1) * 4 + 3 == 3
        
        # Slot 2, outputs 0-3 -> buses 4-7
        assert (2 - 1) * 4 + 0 == 4
        assert (2 - 1) * 4 + 1 == 5
        assert (2 - 1) * 4 + 2 == 6
        assert (2 - 1) * 4 + 3 == 7
        
        # Slot 4, outputs 0-3 -> buses 12-15
        assert (4 - 1) * 4 + 0 == 12
        assert (4 - 1) * 4 + 1 == 13
        assert (4 - 1) * 4 + 2 == 14
        assert (4 - 1) * 4 + 3 == 15


class TestModGeneratorLoaders:
    """Test mod generator JSON loaders."""
    
    def test_lfo_synthdef(self):
        """LFO should have correct synthdef name."""
        assert get_mod_generator_synthdef("LFO") == "ne_mod_lfo"
        
    def test_sloth_synthdef(self):
        """Sloth should have correct synthdef name."""
        assert get_mod_generator_synthdef("Sloth") == "ne_mod_sloth"
        
    def test_empty_synthdef(self):
        """Empty should return None for synthdef."""
        assert get_mod_generator_synthdef("Empty") is None
        
    def test_lfo_output_config(self):
        """LFO should have waveform_phase output config."""
        assert get_mod_generator_output_config("LFO") == "waveform_phase"
        
    def test_sloth_output_config(self):
        """Sloth should have fixed output config."""
        assert get_mod_generator_output_config("Sloth") == "fixed"
        
    def test_empty_output_config(self):
        """Empty should have fixed output config."""
        assert get_mod_generator_output_config("Empty") == "fixed"
        
    def test_lfo_custom_params(self):
        """LFO should have clock_mode and rate params."""
        params = get_mod_generator_custom_params("LFO")
        keys = [p['key'] for p in params]
        assert "rate" in keys
        assert "clock_mode" in keys
        
    def test_sloth_custom_params(self):
        """Sloth should have mode param."""
        params = get_mod_generator_custom_params("Sloth")
        keys = [p['key'] for p in params]
        assert "mode" in keys
        
    def test_empty_custom_params(self):
        """Empty should have no custom params."""
        params = get_mod_generator_custom_params("Empty")
        assert params == []
        
    def test_output_labels_lfo(self):
        """LFO output labels should be A/B/C/D."""
        assert get_mod_output_labels("LFO") == ["A", "B", "C", "D"]
        
    def test_output_labels_sloth(self):
        """Sloth output labels should be X/Y/Z/R."""
        assert get_mod_output_labels("Sloth") == ["X", "Y", "Z", "R"]


class TestStepsQuantization:
    """Test stepped parameter quantization in map_value."""
    
    def test_steps_quantization_3_steps(self):
        """3-step param (like Sloth mode) should quantize to 0, 1, or 2."""
        from src.config import map_value
        p = {"min": 0, "max": 2, "steps": 3, "curve": "lin", "default": 0}
        
        # 0.00-0.24 -> 0
        assert map_value(0.00, p) == 0
        assert map_value(0.24, p) == 0
        
        # 0.25-0.74 -> 1
        assert map_value(0.26, p) == 1
        assert map_value(0.50, p) == 1
        assert map_value(0.74, p) == 1
        
        # 0.75-1.00 -> 2
        assert map_value(0.76, p) == 2
        assert map_value(1.00, p) == 2
    
    def test_no_steps_continuous(self):
        """Param without steps should remain continuous."""
        from src.config import map_value
        p = {"min": 0, "max": 1, "curve": "lin", "default": 0.5}
        
        assert map_value(0.33, p) == pytest.approx(0.33, rel=0.01)
        assert map_value(0.77, p) == pytest.approx(0.77, rel=0.01)
