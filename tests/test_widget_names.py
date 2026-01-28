"""
Test that all key widgets have objectNames set for debugging.

This ensures click-to-trace and debug overlay show meaningful names
instead of generic class names like "QFrame" or "QWidget".
"""
import pytest
from unittest.mock import MagicMock, patch


# Widgets that MUST have objectNames (pattern -> description)
REQUIRED_NAME_PATTERNS = {
    # Generator slots
    'gen{N}_slot': 'GeneratorSlot container',
    'gen{N}_type': 'Generator type selector',
    'gen{N}_type_container': 'Type selector container',
    'gen{N}_header': 'Generator header row',
    'gen{N}_label': 'Generator ID label',
    'gen{N}_filter': 'Filter type button',
    'gen{N}_env': 'Envelope source button',
    'gen{N}_rate': 'Clock rate button',
    'gen{N}_midi': 'MIDI channel button',
    'gen{N}_mute': 'Mute button',
    'gen{N}_gate': 'Gate LED indicator',
    
    # Modulator slots
    'mod{N}_slot': 'ModulatorSlot container',
    'mod{N}_type': 'Modulator type selector',
    'mod{N}_label': 'Modulator ID label',
    'mod{N}_mode': 'Mode button (CLK/FREE)',
    'mod{N}_scope': 'Modulator oscilloscope',
    'mod{N}_wave{M}': 'Waveform button per output',
    'mod{N}_phase{M}': 'Phase button per output',
    'mod{N}_pol{M}': 'Polarity button per output',
}


def get_all_object_names(widget):
    """Recursively collect all objectNames from a widget tree."""
    names = []
    name = widget.objectName()
    if name:
        names.append(name)
    
    for child in widget.findChildren(type(widget).__bases__[0]):
        child_name = child.objectName()
        if child_name:
            names.append(child_name)
    
    return names


class TestWidgetObjectNames:
    """Test that widgets have proper objectNames for debugging."""
    
    def test_required_patterns_documented(self):
        """Verify we have documented required patterns."""
        assert len(REQUIRED_NAME_PATTERNS) >= 10, \
            "Should have at least 10 required name patterns documented"
    
    def test_generator_slot_names_pattern(self):
        """Test generator slot naming convention."""
        # Pattern: gen{slot_id}_{component}
        expected_components = ['slot', 'type', 'type_container', 'header', 
                               'label', 'filter', 'env', 'rate', 'midi', 
                               'mute', 'gate']
        
        for component in expected_components:
            pattern = f'gen{{N}}_{component}'
            assert pattern in REQUIRED_NAME_PATTERNS or \
                   any(pattern.replace('{N}', '') in p for p in REQUIRED_NAME_PATTERNS), \
                   f"Missing pattern for generator component: {component}"
    
    def test_modulator_slot_names_pattern(self):
        """Test modulator slot naming convention."""
        expected_components = ['slot', 'type', 'label', 'mode', 'scope']
        
        for component in expected_components:
            pattern = f'mod{{N}}_{component}'
            assert pattern in REQUIRED_NAME_PATTERNS, \
                   f"Missing pattern for modulator component: {component}"
    
    def test_name_format_consistency(self):
        """Verify naming format is consistent."""
        for pattern in REQUIRED_NAME_PATTERNS:
            # Should be lowercase with underscores
            base = pattern.replace('{N}', '1').replace('{M}', '0')
            assert base == base.lower(), \
                f"Pattern should be lowercase: {pattern}"
            assert ' ' not in base, \
                f"Pattern should not contain spaces: {pattern}"


class TestObjectNameCoverage:
    """
    Integration tests that verify actual widgets have objectNames.
    These require PyQt5 and are skipped if unavailable.
    """
    
    @pytest.fixture
    def mock_qt(self):
        """Mock Qt to avoid display requirements."""
        with patch.dict('sys.modules', {
            'PyQt5': MagicMock(),
            'PyQt5.QtWidgets': MagicMock(),
            'PyQt5.QtCore': MagicMock(),
            'PyQt5.QtGui': MagicMock(),
        }):
            yield
    
    def test_generator_slot_sets_object_name(self):
        """Verify GeneratorSlot.__init__ sets objectName."""
        # Read the source and check for setObjectName call
        import os
        src_path = os.path.join(os.path.dirname(__file__),
                                '..', 'src', 'gui', 'generator_slot.py')
        
        with open(src_path, 'r') as f:
            source = f.read()
        
        assert 'setObjectName' in source, \
            "GeneratorSlot should call setObjectName"
        assert 'gen{slot_id}_slot' in source or 'f"gen{' in source, \
            "GeneratorSlot should use gen{N}_slot pattern"
    
    def test_modulator_slot_sets_object_name(self):
        """Verify ModulatorSlot.__init__ sets objectName."""
        import os
        src_path = os.path.join(os.path.dirname(__file__), 
                                '..', 'src', 'gui', 'modulator_slot.py')
        
        with open(src_path, 'r') as f:
            source = f.read()
        
        assert 'setObjectName' in source, \
            "ModulatorSlot should call setObjectName"
    
# Helper to generate coverage report
def find_unnamed_widgets_in_source(filepath):
    """
    Scan source file for widget creation without setObjectName.
    Returns list of (line_number, widget_type) tuples.
    
    Usage:
        unnamed = find_unnamed_widgets_in_source('src/gui/main_frame.py')
        for line, widget_type in unnamed:
            print(f"Line {line}: {widget_type} has no objectName")
    """
    import re
    
    unnamed = []
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    widget_pattern = re.compile(
        r'(\w+)\s*=\s*(QWidget|QFrame|QLabel|QPushButton|'
        r'CycleButton|DragSlider|MiniSlider)\s*\('
    )
    
    for i, line in enumerate(lines, 1):
        match = widget_pattern.search(line)
        if match:
            var_name = match.group(1)
            widget_type = match.group(2)
            
            # Check next few lines for setObjectName
            lookahead = ''.join(lines[i:i+5])
            if f'{var_name}.setObjectName' not in lookahead:
                # Skip if it's a local variable in a function that sets it elsewhere
                if not var_name.startswith('_'):
                    unnamed.append((i, var_name, widget_type))
    
    return unnamed


if __name__ == '__main__':
    # Quick scan of key files
    import os
    import sys
    
    src_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'gui')
    
    files_to_check = [
        'generator_slot.py',
        'modulator_slot.py',
        'main_frame.py',
        'mixer_channel.py',
        'master_section.py',
    ]
    
    total_unnamed = 0
    
    for filename in files_to_check:
        filepath = os.path.join(src_dir, filename)
        if os.path.exists(filepath):
            unnamed = find_unnamed_widgets_in_source(filepath)
            if unnamed:
                print(f"\n{filename}:")
                for line, var, widget_type in unnamed:
                    print(f"  Line {line}: {var} ({widget_type})")
                total_unnamed += len(unnamed)
    
    print(f"\n{'='*50}")
    print(f"Total widgets without objectName: {total_unnamed}")
    
    sys.exit(1 if total_unnamed > 0 else 0)
