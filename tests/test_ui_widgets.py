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
