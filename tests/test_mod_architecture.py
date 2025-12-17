"""
Comprehensive tests for modulation system architecture.

Tests SSOT compliance, quadrature consistency, invert/polarity defaults,
and cross-layer alignment between Python config, SC files, and UI.
"""

import os
import re
import pytest

from src.config import (
    MOD_SLOT_COUNT,
    MOD_OUTPUTS_PER_SLOT,
    MOD_BUS_COUNT,
    MOD_POLARITY,
    MOD_POLARITY_INDEX,
    MOD_OUTPUT_LABELS,
    MOD_GENERATOR_CYCLE,
    MOD_LFO_WAVEFORMS,
    MOD_LFO_PHASES,
    MOD_LFO_PHASE_PATTERNS,
    MOD_CLOCK_RATES,
    MOD_CLOCK_TICKS_PER_CYCLE,
    get_mod_generator_output_config,
    get_mod_output_labels,
)


class TestQuadratureArchitecture:
    """Tests for 4-output quadrature architecture consistency."""

    def test_outputs_per_slot_is_four(self):
        """System must have exactly 4 outputs per slot."""
        assert MOD_OUTPUTS_PER_SLOT == 4

    def test_bus_count_derived_from_ssot(self):
        """Bus count must be derived, not hardcoded."""
        assert MOD_BUS_COUNT == MOD_SLOT_COUNT * MOD_OUTPUTS_PER_SLOT

    def test_all_output_labels_have_four_elements(self):
        """Every generator's output labels must have exactly 4 elements."""
        for gen_name, labels in MOD_OUTPUT_LABELS.items():
            assert len(labels) == 4, f"{gen_name} has {len(labels)} labels, expected 4"

    def test_lfo_labels_are_abcd(self):
        """LFO outputs should be A, B, C, D."""
        assert MOD_OUTPUT_LABELS["LFO"] == ["A", "B", "C", "D"]

    def test_sloth_labels_are_xyzr(self):
        """Sloth outputs should be X, Y, Z, R."""
        assert MOD_OUTPUT_LABELS["Sloth"] == ["X", "Y", "Z", "R"]

    def test_empty_labels_are_abcd(self):
        """Empty outputs should be A, B, C, D."""
        assert MOD_OUTPUT_LABELS["Empty"] == ["A", "B", "C", "D"]

    def test_phase_patterns_have_four_phases(self):
        """All LFO phase patterns must have exactly 4 phase values."""
        for pattern_name, phases in MOD_LFO_PHASE_PATTERNS.items():
            assert len(phases) == 4, f"Pattern {pattern_name} has {len(phases)} phases"

    def test_get_mod_output_labels_returns_four(self):
        """get_mod_output_labels must return 4-element list for all generators."""
        for gen_name in MOD_GENERATOR_CYCLE:
            labels = get_mod_output_labels(gen_name)
            assert len(labels) == 4, f"{gen_name} returns {len(labels)} labels"


class TestBusIndexCalculation:
    """Tests for bus index formula: (slot - 1) * 4 + output."""

    def test_slot1_outputs(self):
        """Slot 1 outputs map to buses 0-3."""
        for output in range(4):
            assert (1 - 1) * 4 + output == output

    def test_slot2_outputs(self):
        """Slot 2 outputs map to buses 4-7."""
        for output in range(4):
            assert (2 - 1) * 4 + output == 4 + output

    def test_slot3_outputs(self):
        """Slot 3 outputs map to buses 8-11."""
        for output in range(4):
            assert (3 - 1) * 4 + output == 8 + output

    def test_slot4_outputs(self):
        """Slot 4 outputs map to buses 12-15."""
        for output in range(4):
            assert (4 - 1) * 4 + output == 12 + output

    def test_max_bus_index(self):
        """Maximum bus index should be MOD_BUS_COUNT - 1."""
        max_slot = MOD_SLOT_COUNT
        max_output = MOD_OUTPUTS_PER_SLOT - 1
        max_bus = (max_slot - 1) * MOD_OUTPUTS_PER_SLOT + max_output
        assert max_bus == MOD_BUS_COUNT - 1

    def test_reverse_calculation_slot(self):
        """Can recover slot from bus index."""
        for bus_idx in range(MOD_BUS_COUNT):
            slot = (bus_idx // MOD_OUTPUTS_PER_SLOT) + 1
            assert 1 <= slot <= MOD_SLOT_COUNT

    def test_reverse_calculation_output(self):
        """Can recover output from bus index."""
        for bus_idx in range(MOD_BUS_COUNT):
            output = bus_idx % MOD_OUTPUTS_PER_SLOT
            assert 0 <= output < MOD_OUTPUTS_PER_SLOT


class TestInvertPolarity:
    """Tests for invert/polarity naming and defaults."""

    def test_polarity_values_are_norm_inv(self):
        """MOD_POLARITY must be NORM/INV, not UNI/BI."""
        assert MOD_POLARITY == ["NORM", "INV"]

    def test_polarity_index_norm_is_zero(self):
        """NORM must be index 0 (default)."""
        assert MOD_POLARITY_INDEX["NORM"] == 0

    def test_polarity_index_inv_is_one(self):
        """INV must be index 1."""
        assert MOD_POLARITY_INDEX["INV"] == 1

    def test_no_uni_bi_in_polarity(self):
        """UNI/BI must not appear in polarity constants."""
        assert "UNI" not in MOD_POLARITY
        assert "BI" not in MOD_POLARITY
        assert "UNI" not in MOD_POLARITY_INDEX
        assert "BI" not in MOD_POLARITY_INDEX


class TestSCFileConsistency:
    """Tests that SC files match Python config expectations."""

    @pytest.fixture
    def sc_core_dir(self):
        """Path to supercollider/core directory."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, 'supercollider', 'core')

    def test_lfo_polarity_defaults_to_zero(self, sc_core_dir):
        """mod_lfo.scd polarity args should default to 0 (NORM)."""
        lfo_path = os.path.join(sc_core_dir, 'mod_lfo.scd')
        with open(lfo_path, 'r') as f:
            content = f.read()
        
        # Find the arg line with polarity defaults
        match = re.search(r'polarityA\s*=\s*(\d)', content)
        assert match, "Could not find polarityA default in mod_lfo.scd"
        assert match.group(1) == '0', f"polarityA defaults to {match.group(1)}, expected 0"

    def test_sloth_polarity_defaults_to_zero(self, sc_core_dir):
        """mod_sloth.scd polarity args should default to 0 (NORM)."""
        sloth_path = os.path.join(sc_core_dir, 'mod_sloth.scd')
        with open(sloth_path, 'r') as f:
            content = f.read()
        
        match = re.search(r'polarityX\s*=\s*(\d)', content)
        assert match, "Could not find polarityX default in mod_sloth.scd"
        assert match.group(1) == '0', f"polarityX defaults to {match.group(1)}, expected 0"

    def test_slots_state_defaults_to_zero(self, sc_core_dir):
        """mod_slots.scd output state polarity should default to 0."""
        slots_path = os.path.join(sc_core_dir, 'mod_slots.scd')
        with open(slots_path, 'r') as f:
            content = f.read()
        
        # Check Dictionary defaults
        matches = re.findall(r'\\polarity,\s*(\d)', content)
        assert len(matches) >= 4, "Expected at least 4 polarity defaults in mod_slots.scd"
        for i, val in enumerate(matches[:4]):
            assert val == '0', f"Output {i} polarity defaults to {val}, expected 0"

    def test_no_uni_bi_comments_in_sc(self, sc_core_dir):
        """SC files should use NORM/INV comments, not UNI/BI."""
        for filename in ['mod_lfo.scd', 'mod_sloth.scd', 'mod_osc.scd']:
            filepath = os.path.join(sc_core_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    content = f.read()
                # Allow UNI/BI only if NORM/INV also present (transitional)
                if '0=UNI' in content or '1=BI' in content:
                    assert '0=NORM' in content or '1=INV' in content, \
                        f"{filename} uses UNI/BI without NORM/INV"

    def test_sc_uses_python_addr_not_listen_port(self, sc_core_dir):
        """mod_osc.scd should use ~pythonAddr, not ~pythonListenPort."""
        osc_path = os.path.join(sc_core_dir, 'mod_osc.scd')
        with open(osc_path, 'r') as f:
            content = f.read()
        
        assert '~pythonListenPort' not in content, \
            "mod_osc.scd still references undefined ~pythonListenPort"


class TestPythonUIConsistency:
    """Tests that Python UI matches config expectations."""

    @pytest.fixture
    def gui_dir(self):
        """Path to src/gui directory."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, 'src', 'gui')

    def test_modulator_slot_builder_default_polarity_zero(self, gui_dir):
        """modulator_slot_builder.py should default polarity to 0."""
        builder_path = os.path.join(gui_dir, 'modulator_slot_builder.py')
        with open(builder_path, 'r') as f:
            content = f.read()
        
        # Check that default_polarity is set to 0
        assert 'default_polarity = 0' in content, \
            "modulator_slot_builder.py should set default_polarity = 0"

    def test_modulator_slot_builder_no_hardcoded_one_default(self, gui_dir):
        """modulator_slot_builder.py should not default polarity to 1."""
        builder_path = os.path.join(gui_dir, 'modulator_slot_builder.py')
        with open(builder_path, 'r') as f:
            content = f.read()
        
        # Should not have the old conditional that defaulted to 1
        assert 'else 1' not in content or 'default_polarity' not in content.split('else 1')[0][-50:], \
            "modulator_slot_builder.py may still default polarity to 1"

    def test_tooltip_says_invert_not_polarity(self, gui_dir):
        """Tooltip should describe NORM/INV invert, not UNI/BI polarity."""
        builder_path = os.path.join(gui_dir, 'modulator_slot_builder.py')
        with open(builder_path, 'r') as f:
            content = f.read()
        
        # Should have invert terminology
        assert 'Invert' in content or 'invert' in content or 'NORM' in content, \
            "Tooltip should mention invert/NORM/INV"
        # Should not have old UNI/BI terminology in tooltips
        assert 'UNI (0→1)' not in content, \
            "Tooltip still references UNI (0→1)"

    def test_mod_scope_no_hardcoded_colors(self, gui_dir):
        """mod_scope.py should not hardcode trace colors."""
        scope_path = os.path.join(gui_dir, 'mod_scope.py')
        with open(scope_path, 'r') as f:
            content = f.read()
        
        # Should not have fallback colors in .get() calls
        assert "'#00ff00'" not in content, \
            "mod_scope.py has hardcoded green fallback"
        assert "'#ff6600'" not in content, \
            "mod_scope.py has hardcoded orange fallback"


class TestClockRatesConsistency:
    """Tests for clock rate configuration consistency."""

    def test_clock_rates_and_ticks_same_length(self):
        """MOD_CLOCK_RATES and MOD_CLOCK_TICKS_PER_CYCLE must match."""
        assert len(MOD_CLOCK_RATES) == len(MOD_CLOCK_TICKS_PER_CYCLE)

    def test_ticks_decrease_with_rate(self):
        """Faster rates should have fewer ticks per cycle."""
        for i in range(len(MOD_CLOCK_TICKS_PER_CYCLE) - 1):
            assert MOD_CLOCK_TICKS_PER_CYCLE[i] > MOD_CLOCK_TICKS_PER_CYCLE[i + 1], \
                f"Ticks should decrease: {MOD_CLOCK_RATES[i]} vs {MOD_CLOCK_RATES[i+1]}"

    def test_slowest_rate_is_division(self):
        """First rate should be a division (slow)."""
        assert MOD_CLOCK_RATES[0].startswith('/'), \
            f"First rate should be division, got {MOD_CLOCK_RATES[0]}"

    def test_fastest_rate_is_multiplication(self):
        """Last rate should be a multiplication (fast)."""
        assert MOD_CLOCK_RATES[-1].startswith('x'), \
            f"Last rate should be multiplication, got {MOD_CLOCK_RATES[-1]}"


class TestModGeneratorConfigs:
    """Tests for mod generator JSON config loading."""

    def test_all_cycle_generators_have_config(self):
        """Every generator in MOD_GENERATOR_CYCLE should have output config."""
        for gen_name in MOD_GENERATOR_CYCLE:
            config = get_mod_generator_output_config(gen_name)
            assert config is not None, f"{gen_name} has no output config"

    def test_lfo_output_config_is_pattern_rotate(self):
        """LFO should use pattern_rotate output config."""
        assert get_mod_generator_output_config("LFO") == "pattern_rotate"

    def test_sloth_output_config_is_fixed(self):
        """Sloth should use fixed output config."""
        assert get_mod_generator_output_config("Sloth") == "fixed"

    def test_empty_output_config_is_fixed(self):
        """Empty should use fixed output config."""
        assert get_mod_generator_output_config("Empty") == "fixed"


class TestModRoutingState:
    """Tests for ModConnection dataclass."""

    def test_mod_connection_has_invert_field(self):
        """ModConnection should have invert field."""
        from src.gui.mod_routing_state import ModConnection
        conn = ModConnection(source_bus=0, target_slot=1, target_param="frequency")
        assert hasattr(conn, 'invert')

    def test_mod_connection_invert_default_false(self):
        """ModConnection invert should default to False."""
        from src.gui.mod_routing_state import ModConnection
        conn = ModConnection(source_bus=0, target_slot=1, target_param="frequency")
        assert conn.invert == False

    def test_mod_connection_has_polarity_field(self):
        """ModConnection should have polarity field."""
        from src.gui.mod_routing_state import ModConnection
        conn = ModConnection(source_bus=0, target_slot=1, target_param="frequency")
        assert hasattr(conn, 'polarity')

    def test_mod_connection_polarity_default_bipolar(self):
        """ModConnection polarity should default to 'bipolar'."""
        from src.gui.mod_routing_state import ModConnection
        conn = ModConnection(source_bus=0, target_slot=1, target_param="frequency")
        assert conn.polarity.value == 0  # BIPOLAR

    def test_mod_connection_effective_range(self):
        """ModConnection effective_range should be depth * amount."""
        from src.gui.mod_routing_state import ModConnection
        conn = ModConnection(
            source_bus=0, target_slot=1, target_param="frequency",
            depth=0.5, amount=0.8
        )
        assert abs(conn.effective_range - 0.4) < 0.001


class TestSSOTCompliance:
    """Tests that Single Source of Truth principles are followed."""

    def test_bus_count_not_hardcoded_twelve(self):
        """MOD_BUS_COUNT should not be hardcoded to old value 12."""
        assert MOD_BUS_COUNT != 12, "MOD_BUS_COUNT appears to be old 3-output value"

    def test_outputs_not_hardcoded_three(self):
        """MOD_OUTPUTS_PER_SLOT should not be hardcoded to old value 3."""
        assert MOD_OUTPUTS_PER_SLOT != 3, "MOD_OUTPUTS_PER_SLOT appears to be old value"

    def test_lfo_has_eight_waveforms(self):
        """LFO should have 8 waveforms (Saw, Ramp, Sqr, Tri, Sin, Rect+, Rect-, S&H)."""
        assert len(MOD_LFO_WAVEFORMS) == 8

    def test_lfo_has_eight_phases(self):
        """LFO should have 8 phase options (0, 45, 90, ... 315)."""
        assert len(MOD_LFO_PHASES) == 8
        assert MOD_LFO_PHASES == [0, 45, 90, 135, 180, 225, 270, 315]
