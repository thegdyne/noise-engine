#!/usr/bin/env python3
"""
CI script to check widget objectName coverage.

Run as: python tools/check_widget_names.py

Exit codes:
  0 - All widgets named (or under threshold)
  1 - Too many unnamed widgets

The threshold allows gradual adoption - decrease it as you add names.
"""
import os
import re
import sys

# Current threshold - decrease as you add objectNames
# Goal: get to 0
UNNAMED_THRESHOLD = 70  # Started at 68, allow small buffer

# Files to check
GUI_FILES = [
    'generator_slot_builder.py',
    'generator_slot.py',
    'modulator_slot_builder.py',
    'modulator_slot.py',
    'main_frame.py',
    'mixer_channel.py',
    'master_section.py',
    'channel_strip.py',
]


def find_unnamed_widgets(filepath):
    """Find widgets created without setObjectName."""
    unnamed = []
    
    if not os.path.exists(filepath):
        return unnamed
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Match: var = WidgetType(
    widget_pattern = re.compile(
        r'(\w+)\s*=\s*(QWidget|QFrame|QLabel|QPushButton|'
        r'CycleButton|DragSlider|MiniSlider|QSlider)\s*\('
    )
    
    for i, line in enumerate(lines, 1):
        match = widget_pattern.search(line)
        if match:
            var_name = match.group(1)
            widget_type = match.group(2)
            
            # Check next 5 lines for setObjectName
            lookahead = ''.join(lines[i:i+5])
            if f'{var_name}.setObjectName' not in lookahead:
                # Skip internal/temp variables
                if not var_name.startswith('_') and var_name != 'self':
                    unnamed.append((i, var_name, widget_type))
    
    return unnamed


def main():
    # Find src/gui directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    gui_dir = os.path.join(repo_root, 'src', 'gui')
    
    if not os.path.isdir(gui_dir):
        print(f"ERROR: Cannot find {gui_dir}")
        return 1
    
    total_unnamed = 0
    results = {}
    
    for filename in GUI_FILES:
        filepath = os.path.join(gui_dir, filename)
        unnamed = find_unnamed_widgets(filepath)
        if unnamed:
            results[filename] = unnamed
            total_unnamed += len(unnamed)
    
    # Print report
    print("Widget objectName Coverage Report")
    print("=" * 50)
    
    if results:
        for filename, unnamed in sorted(results.items()):
            print(f"\n{filename}:")
            for line, var, widget_type in unnamed:
                print(f"  Line {line}: {var} ({widget_type})")
    else:
        print("\n✅ All widgets have objectNames!")
    
    print("\n" + "=" * 50)
    print(f"Total unnamed: {total_unnamed} / threshold: {UNNAMED_THRESHOLD}")
    
    if total_unnamed > UNNAMED_THRESHOLD:
        print(f"\n❌ FAIL: {total_unnamed} unnamed widgets exceeds threshold of {UNNAMED_THRESHOLD}")
        print("   Add setObjectName() calls or increase threshold temporarily.")
        return 1
    elif total_unnamed > 0:
        print(f"\n⚠️  WARN: {total_unnamed} unnamed widgets (under threshold)")
        print("   Consider adding objectNames for better debugging.")
        return 0
    else:
        print("\n✅ PASS: All widgets have objectNames!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
