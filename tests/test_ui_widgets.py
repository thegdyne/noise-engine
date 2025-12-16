"""
Tests for UI widget behaviors.

These tests verify widget configuration without requiring a running Qt application.
They parse the source code to check that required configurations are in place.
"""

import pytest
import os
import re
import ast


class TestDoubleClickReset:
    """Verify all sliders that should reset on double-click have the behavior configured."""
    
    # Sliders that MUST have double-click reset configured
    REQUIRED_DOUBLE_CLICK_SLIDERS = {
        'master_section.py': [
            ('eq_lo_slider', 120, '0dB center'),
            ('eq_mid_slider', 120, '0dB center'),
            ('eq_hi_slider', 120, '0dB center'),
        ],
        'mixer_panel.py': [
            # Pan slider uses custom PanSlider class with mouseDoubleClickEvent
            ('pan_slider', 0, 'center'),
        ],
    }
    
    def test_eq_sliders_have_double_click_reset(self, project_root):
        """EQ sliders (LO, MID, HI) must reset to 0dB on double-click."""
        filepath = os.path.join(project_root, 'src', 'gui', 'master_section.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        for slider_name in ['eq_lo_slider', 'eq_mid_slider', 'eq_hi_slider']:
            # Check for setDoubleClickValue(120) - 120 = 0dB for 0-240 range
            pattern = rf'self\.{slider_name}\.setDoubleClickValue\s*\(\s*120\s*\)'
            assert re.search(pattern, content), \
                f"{slider_name} must have setDoubleClickValue(120) for 0dB reset"
    
    def test_pan_slider_has_double_click_reset(self, project_root):
        """Pan slider must reset to center on double-click."""
        filepath = os.path.join(project_root, 'src', 'gui', 'mixer_panel.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Check for PanSlider class with mouseDoubleClickEvent that sets value to 0
        assert 'class PanSlider' in content, \
            "PanSlider class must exist for double-click behavior"
        assert 'mouseDoubleClickEvent' in content, \
            "PanSlider must override mouseDoubleClickEvent"
        assert 'setValue(0)' in content, \
            "PanSlider mouseDoubleClickEvent must reset to 0 (center)"


class TestDragSliderPopups:
    """Verify DragSlider has popup support methods."""
    
    def test_drag_slider_has_show_drag_value_method(self, project_root):
        """DragSlider must have show_drag_value() method for handler-driven popups."""
        filepath = os.path.join(project_root, 'src', 'gui', 'widgets.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert 'def show_drag_value(self, text)' in content, \
            "DragSlider must have show_drag_value(self, text) method"
    
    def test_master_faders_call_show_drag_value(self, project_root):
        """Master section fader handlers must call show_drag_value()."""
        filepath = os.path.join(project_root, 'src', 'gui', 'master_section.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        required_popups = [
            ('master_fader', '_on_fader_changed'),
            ('ceiling_fader', '_on_ceiling_changed'),
            ('eq_lo_slider', '_on_eq_lo_changed'),
            ('eq_mid_slider', '_on_eq_mid_changed'),
            ('eq_hi_slider', '_on_eq_hi_changed'),
            ('comp_threshold', '_on_comp_threshold_changed'),
            ('comp_makeup', '_on_comp_makeup_changed'),
        ]
        
        for slider_name, handler_name in required_popups:
            pattern = rf'self\.{slider_name}\.show_drag_value\s*\('
            assert re.search(pattern, content), \
                f"{slider_name} must call show_drag_value() in {handler_name}"
    
    def test_mixer_faders_call_show_drag_value(self, project_root):
        """Mixer channel fader handlers must call show_drag_value()."""
        filepath = os.path.join(project_root, 'src', 'gui', 'mixer_panel.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert 'self.fader.show_drag_value(' in content, \
            "Mixer channel fader must call show_drag_value()"


class TestSliderRanges:
    """Verify slider ranges are correctly configured."""
    
    def test_eq_sliders_have_correct_range(self, project_root):
        """EQ sliders must have 0-240 range (for -12dB to +12dB)."""
        filepath = os.path.join(project_root, 'src', 'gui', 'master_section.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        for slider_name in ['eq_lo_slider', 'eq_mid_slider', 'eq_hi_slider']:
            pattern = rf'self\.{slider_name}\.setRange\s*\(\s*0\s*,\s*240\s*\)'
            assert re.search(pattern, content), \
                f"{slider_name} must have range 0-240"
    
    def test_pan_slider_has_correct_range(self, project_root):
        """Pan slider must have -100 to 100 range."""
        filepath = os.path.join(project_root, 'src', 'gui', 'mixer_panel.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert 'setRange(-100, 100)' in content, \
            "Pan slider must have range -100 to 100"


class TestHeightRatioSensitivity:
    """Verify faders use height-ratio sensitivity, not fixed pixel values."""
    
    def test_drag_slider_uses_height_ratio(self, project_root):
        """DragSlider must calculate sensitivity from fader height, not fixed pixels."""
        filepath = os.path.join(project_root, 'src', 'gui', 'widgets.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Should use self.height() for sensitivity calculation
        assert 'self.height()' in content, \
            "DragSlider must use self.height() for sensitivity calculation"
        
        # Should NOT use fixed DRAG_SENSITIVITY values in mouseMoveEvent
        # (Old pattern was: travel = DRAG_SENSITIVITY['slider_normal'])
        assert "DRAG_SENSITIVITY['slider_normal']" not in content or \
               "DRAG_SENSITIVITY['slider_fine']" not in content, \
            "DragSlider should not use fixed DRAG_SENSITIVITY values for height-ratio mode"


class TestMiniKnob:
    """Verify MiniKnob widget behavior for channel strip EQ."""
    
    def test_miniknob_has_double_click_reset(self, project_root):
        """MiniKnob must reset to default (100 = unity) on double-click."""
        filepath = os.path.join(project_root, 'src', 'gui', 'widgets.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # MiniKnob should have mouseDoubleClickEvent that resets to default
        assert 'class MiniKnob' in content, \
            "MiniKnob class must exist"
        assert 'mouseDoubleClickEvent' in content, \
            "MiniKnob must override mouseDoubleClickEvent"
        # Check for setValue call in the class context
        assert 'setValue(self._default)' in content or 'setValue(self._default' in content, \
            "MiniKnob mouseDoubleClickEvent must reset to default value"
    
    def test_miniknob_default_value(self, project_root):
        """MiniKnob default value should be 100 (unity gain)."""
        filepath = os.path.join(project_root, 'src', 'gui', 'widgets.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert '_default = 100' in content, \
            "MiniKnob default value should be 100 (unity)"
    
    def test_miniknob_range(self, project_root):
        """MiniKnob range should be 0-200."""
        filepath = os.path.join(project_root, 'src', 'gui', 'widgets.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert '_min = 0' in content, \
            "MiniKnob min should be 0"
        assert '_max = 200' in content, \
            "MiniKnob max should be 200"


class TestCycleButton:
    """Verify CycleButton wrap behavior."""
    
    def test_cyclebutton_wrap_default_true(self, project_root):
        """CycleButton.wrap must default to True."""
        filepath = os.path.join(project_root, 'src', 'gui', 'widgets.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Check that wrap defaults to True in __init__
        assert 'self.wrap = True' in content, \
            "CycleButton.wrap must default to True"
    
    def test_cyclebutton_wraps_forward(self, project_root):
        """CycleButton must wrap from last to first when cycling forward."""
        filepath = os.path.join(project_root, 'src', 'gui', 'widgets.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # cycle_forward should use modulo when wrap=True
        assert '% len(self.values)' in content, \
            "CycleButton must use modulo for wrapping"
    
    def test_cyclebutton_wraps_backward(self, project_root):
        """CycleButton must wrap from first to last when cycling backward."""
        filepath = os.path.join(project_root, 'src', 'gui', 'widgets.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # cycle_backward should also wrap
        assert '(self.index - 1) % len(self.values)' in content, \
            "CycleButton.cycle_backward must wrap using modulo"


class TestModSourceConstants:
    """Verify mod source constants have correct lengths."""
    
    def test_mod_clock_rates_count(self):
        """MOD_CLOCK_RATES must have 12 entries."""
        from src.config import MOD_CLOCK_RATES
        assert len(MOD_CLOCK_RATES) == 12, \
            f"MOD_CLOCK_RATES should have 12 entries, got {len(MOD_CLOCK_RATES)}"
    
    def test_mod_clock_ticks_per_cycle_count(self):
        """MOD_CLOCK_TICKS_PER_CYCLE must have 12 entries."""
        from src.config import MOD_CLOCK_TICKS_PER_CYCLE
        assert len(MOD_CLOCK_TICKS_PER_CYCLE) == 12, \
            f"MOD_CLOCK_TICKS_PER_CYCLE should have 12 entries, got {len(MOD_CLOCK_TICKS_PER_CYCLE)}"
    
    def test_mod_clock_rates_and_ticks_match(self):
        """MOD_CLOCK_RATES and MOD_CLOCK_TICKS_PER_CYCLE must have same length."""
        from src.config import MOD_CLOCK_RATES, MOD_CLOCK_TICKS_PER_CYCLE
        assert len(MOD_CLOCK_RATES) == len(MOD_CLOCK_TICKS_PER_CYCLE), \
            "MOD_CLOCK_RATES and MOD_CLOCK_TICKS_PER_CYCLE must have same length (SSOT)"
    
    def test_mod_lfo_modes_exist(self):
        """MOD_LFO_MODES must be defined with CLK and FREE."""
        from src.config import MOD_LFO_MODES
        assert MOD_LFO_MODES == ["CLK", "FREE"], \
            "MOD_LFO_MODES must be ['CLK', 'FREE']"
    
    def test_mod_lfo_freq_range(self):
        """MOD_LFO_FREQ range must be 0.01-100Hz."""
        from src.config import MOD_LFO_FREQ_MIN, MOD_LFO_FREQ_MAX
        assert MOD_LFO_FREQ_MIN == 0.01, "MOD_LFO_FREQ_MIN should be 0.01 Hz"
        assert MOD_LFO_FREQ_MAX == 100.0, "MOD_LFO_FREQ_MAX should be 100 Hz"


class TestSkinSystem:
    """Verify skin system configuration."""
    
    def test_skin_has_accent_mod_lfo(self, project_root):
        """Skin must have accent_mod_lfo colour."""
        filepath = os.path.join(project_root, 'src', 'gui', 'skins', 'default.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert "'accent_mod_lfo'" in content, \
            "Skin must define accent_mod_lfo colour"
    
    def test_skin_has_accent_mod_sloth(self, project_root):
        """Skin must have accent_mod_sloth colour."""
        filepath = os.path.join(project_root, 'src', 'gui', 'skins', 'default.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert "'accent_mod_sloth'" in content, \
            "Skin must define accent_mod_sloth colour"
    
    def test_colors_dict_has_mod_accents(self, project_root):
        """COLORS dict must include mod accent colours from skin."""
        filepath = os.path.join(project_root, 'src', 'gui', 'theme.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert "'accent_mod_lfo'" in content, \
            "COLORS dict must include accent_mod_lfo"
        assert "'accent_mod_sloth'" in content, \
            "COLORS dict must include accent_mod_sloth"
    
    def test_skin_has_scope_colours(self, project_root):
        """Skin must define scope trace colours."""
        filepath = os.path.join(project_root, 'src', 'gui', 'skins', 'default.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert "'scope_trace_a'" in content, "Skin must define scope_trace_a"
        assert "'scope_trace_b'" in content, "Skin must define scope_trace_b"
        assert "'scope_trace_c'" in content, "Skin must define scope_trace_c"
    
    def test_colors_dict_built_from_skin(self, project_root):
        """COLORS dict must be built from skin, not hardcoded."""
        filepath = os.path.join(project_root, 'src', 'gui', 'theme.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Theme should import skin and use get() function
        assert 'from .skins import active as skin' in content, \
            "theme.py must import active skin"
        assert 'def get(key' in content, \
            "theme.py must have get() function for skin access"


class TestModScopeColours:
    """Verify mod scope uses skin colours, not hardcoded."""
    
    def test_mod_scope_uses_colors_dict(self, project_root):
        """ModScope must use COLORS dict for trace colours."""
        filepath = os.path.join(project_root, 'src', 'gui', 'mod_scope.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Should reference COLORS, not hardcoded hex
        assert "COLORS['scope_trace_a']" in content or \
               "COLORS['scope_trace_b']" in content or \
               "COLORS['scope_trace_c']" in content or \
               "COLORS.get('scope_trace" in content, \
            "ModScope must use COLORS dict for trace colours"
    
    def test_mod_scope_no_hardcoded_trace_colours(self, project_root):
        """ModScope must not hardcode trace colours."""
        filepath = os.path.join(project_root, 'src', 'gui', 'mod_scope.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Should not have hardcoded hex colours for traces
        # (green, cyan, orange typically)
        assert "'#00ff00'" not in content.lower(), \
            "ModScope should not hardcode green trace colour"
        # Note: Some hardcoded colours are acceptable for grids etc, 
        # but trace colours should come from skin


class TestChannelStripOSC:
    """Verify channel strip controls send OSC messages."""
    
    def test_pan_sends_osc_on_change(self, project_root):
        """Pan change handler must send OSC via gen_pan path."""
        import re
        filepath = os.path.join(project_root, 'src', 'gui', 'main_frame.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Extract the function block and verify OSC send is inside it
        m = re.search(r"def on_generator_pan_changed\(.*?\):([\s\S]*?)(\n    def |\Z)", content)
        assert m, "on_generator_pan_changed() function not found"
        block = m.group(1)
        assert "OSC_PATHS['gen_pan']" in block, \
            "Pan handler must use OSC_PATHS['gen_pan']"
        assert "send_message" in block, \
            "Pan handler must call send_message"
    
    def test_eq_sends_osc_on_change(self, project_root):
        """EQ change handler must send OSC messages via SSOT path."""
        import re
        filepath = os.path.join(project_root, 'src', 'gui', 'main_frame.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Extract the function block
        m = re.search(r"def on_generator_eq_changed\(.*?\):([\s\S]*?)(\n    def |\Z)", content)
        assert m, "on_generator_eq_changed() function not found"
        block = m.group(1)
        # Must use OSC_PATHS, not hardcoded path
        assert "OSC_PATHS['gen_strip_eq_base']" in block, \
            "EQ handler must use OSC_PATHS['gen_strip_eq_base']"
        assert "send_message" in block, \
            "EQ handler must call send_message"
    
    def test_mixer_signals_connected(self, project_root):
        """MixerPanel pan/EQ signals must be connected in main_frame."""
        filepath = os.path.join(project_root, 'src', 'gui', 'main_frame.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert 'generator_pan_changed.connect' in content, \
            "MixerPanel pan signal must be connected"
        assert 'generator_eq_changed.connect' in content, \
            "MixerPanel EQ signal must be connected"


class TestModSlotSync:
    """Verify mod slot sync handles different control types."""
    
    def test_sync_handles_cyclebutton_and_slider(self, project_root):
        """Mod slot sync must handle both CycleButton (mode) and DragSlider (rate/shape)."""
        filepath = os.path.join(project_root, 'src', 'gui', 'main_frame.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Must check for get_index (CycleButton) before assuming .value() (DragSlider)
        assert 'get_index' in content, \
            "Sync code must check for get_index() method (CycleButton)"
        assert 'hasattr' in content and 'get_index' in content, \
            "Sync code must use hasattr to detect CycleButton vs DragSlider"
    
    def test_mod_slot_mode_uses_cyclebutton(self, project_root):
        """LFO/Sloth mode param must use CycleButton, not DragSlider."""
        filepath = os.path.join(project_root, 'src', 'gui', 'modulator_slot_builder.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Mode param should create CycleButton for 2 or 3 steps
        assert "key == 'mode'" in content, \
            "Mode param must be detected by key"
        assert 'steps_i in (2, 3)' in content, \
            "Mode must handle both LFO (2 steps) and Sloth (3 steps)"
        assert 'MOD_LFO_MODES' in content, \
            "LFO mode CycleButton must use MOD_LFO_MODES"
        assert 'MOD_SLOTH_MODES' in content, \
            "Sloth mode CycleButton must use MOD_SLOTH_MODES"


class TestStripStatePersistence:
    """Verify mixer strip state persists across generator changes."""
    
    def test_strip_state_sync_exists(self, project_root):
        """_sync_strip_state_to_sc must exist and send pan/EQ/mute/solo/gain."""
        import re
        filepath = os.path.join(project_root, 'src', 'gui', 'main_frame.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Extract the function block
        m = re.search(r"def _sync_strip_state_to_sc\(.*?\):([\s\S]*?)(\n    def |\Z)", content)
        assert m, "_sync_strip_state_to_sc() function not found"
        block = m.group(1)
        
        # Must send all strip params
        assert "gen_pan" in block, "Strip sync must send pan"
        assert "gen_mute" in block, "Strip sync must send mute"
        assert "gen_strip_solo" in block, "Strip sync must send solo"
        assert "gen_gain" in block, "Strip sync must send gain"
        assert "gen_strip_eq_base" in block, "Strip sync must send EQ"
    
    def test_strip_sync_called_on_generator_change(self, project_root):
        """on_generator_changed must call _sync_strip_state_to_sc."""
        import re
        filepath = os.path.join(project_root, 'src', 'gui', 'main_frame.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Extract on_generator_changed function
        m = re.search(r"def on_generator_changed\(.*?\):([\s\S]*?)(\n    def |\Z)", content)
        assert m, "on_generator_changed() function not found"
        block = m.group(1)
        
        assert "_sync_strip_state_to_sc" in block, \
            "on_generator_changed must call _sync_strip_state_to_sc"
    
    def test_channel_strip_has_get_strip_state(self, project_root):
        """ChannelStrip must have get_strip_state method."""
        filepath = os.path.join(project_root, 'src', 'gui', 'mixer_panel.py')
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert 'def get_strip_state(self)' in content, \
            "ChannelStrip must have get_strip_state method"
        assert "'pan'" in content and "'muted'" in content, \
            "get_strip_state must return pan and muted state"
