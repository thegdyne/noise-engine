#!/usr/bin/env python3
"""
Layout Tuning Tool for Noise Engine Generator Slots

Interactive tool to adjust header and slider layout values.
Changes are applied directly to src/gui/theme.py.

Usage:
    python tools/tune_layout.py [command] [amount]
    
Examples:
    python tools/tune_layout.py                  # Show current values
    python tools/tune_layout.py gen right 4      # Move GEN label right by 4
    python tools/tune_layout.py empty left 2     # Move Empty selector left by 2
    python tools/tune_layout.py sliders up 2     # Move sliders up (reduce gap)
    python tools/tune_layout.py reset            # Reset to defaults
"""

import re
import sys
import os

# Path to theme file
THEME_FILE = os.path.join(os.path.dirname(__file__), '..', 'src', 'gui', 'theme.py')

# Default values for reset
DEFAULTS = {
    'header_inset_left': 14,
    'header_inset_right': 6,
    'header_selector_text_pad': 4,
    'header_type_width': 40,
    'header_content_gap': 2,
    'slider_section_spacing': 6,
    'slider_min_height': 38,
    'slider_column_width': 22,
    'slider_gap': 1,
    'content_row_spacing': 2,
    'button_strip_width': 40,
}

# Mapping of friendly commands to theme keys and directions
COMMANDS = {
    # GEN label
    ('gen', 'right'): ('header_inset_left', +1),
    ('gen', 'left'): ('header_inset_left', -1),
    
    # Empty selector box position
    ('empty', 'left'): ('header_inset_right', +1),    # more margin = box moves left
    ('empty', 'right'): ('header_inset_right', -1),   # less margin = box moves right
    
    # Empty text inside box
    ('text', 'right'): ('header_selector_text_pad', +1),
    ('text', 'left'): ('header_selector_text_pad', -1),
    
    # Selector box size
    ('selector', 'wider'): ('header_type_width', +2),
    ('selector', 'narrower'): ('header_type_width', -2),
    
    # Sliders vertical position (header-to-sliders gap)
    ('sliders', 'up'): ('header_content_gap', -1),
    ('sliders', 'down'): ('header_content_gap', +1),
    
    # Gap between P1-P5 and FRQ-DEC rows
    ('rows', 'closer'): ('slider_section_spacing', -1),
    ('rows', 'apart'): ('slider_section_spacing', +1),
    
    # Slider height
    ('sliders', 'shorter'): ('slider_min_height', -2),
    ('sliders', 'taller'): ('slider_min_height', +2),
    
    # Slider columns
    ('columns', 'narrower'): ('slider_column_width', -1),
    ('columns', 'wider'): ('slider_column_width', +1),
    
    # Gap between slider columns
    ('columns', 'closer'): ('slider_gap', -1),
    ('columns', 'apart'): ('slider_gap', +1),
    
    # Button strip
    ('buttons', 'narrower'): ('button_strip_width', -2),
    ('buttons', 'wider'): ('button_strip_width', +2),
    
    # Sliders to buttons gap
    ('buttons', 'closer'): ('content_row_spacing', -1),
    ('buttons', 'apart'): ('content_row_spacing', +1),
}


def read_theme_value(key):
    """Read current value of a theme key from theme.py"""
    with open(THEME_FILE, 'r') as f:
        content = f.read()
    
    pattern = rf"'{key}':\s*(\d+)"
    match = re.search(pattern, content)
    if match:
        return int(match.group(1))
    return None


def write_theme_value(key, value):
    """Write a new value for a theme key to theme.py"""
    with open(THEME_FILE, 'r') as f:
        content = f.read()
    
    # Ensure value doesn't go negative
    value = max(0, value)
    
    pattern = rf"('{key}':\s*)\d+"
    new_content = re.sub(pattern, rf"\g<1>{value}", content)
    
    with open(THEME_FILE, 'w') as f:
        f.write(new_content)
    
    return value


def show_current_values():
    """Display all current layout values"""
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║              NOISE ENGINE LAYOUT VALUES                      ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    
    print("║  HEADER                                                      ║")
    print(f"║    header_inset_left:       {read_theme_value('header_inset_left'):3}  (gen right/left)          ║")
    print(f"║    header_inset_right:      {read_theme_value('header_inset_right'):3}  (empty left/right)        ║")
    print(f"║    header_selector_text_pad:{read_theme_value('header_selector_text_pad'):3}  (text right/left)         ║")
    print(f"║    header_type_width:       {read_theme_value('header_type_width'):3}  (selector wider/narrower) ║")
    print(f"║    header_content_gap:      {read_theme_value('header_content_gap'):3}  (sliders up/down)         ║")
    
    print("║                                                              ║")
    print("║  SLIDERS                                                     ║")
    print(f"║    slider_section_spacing:  {read_theme_value('slider_section_spacing'):3}  (rows closer/apart)       ║")
    print(f"║    slider_min_height:       {read_theme_value('slider_min_height'):3}  (sliders shorter/taller)  ║")
    print(f"║    slider_column_width:     {read_theme_value('slider_column_width'):3}  (columns wider/narrower)  ║")
    print(f"║    slider_gap:              {read_theme_value('slider_gap'):3}  (columns closer/apart)    ║")
    
    print("║                                                              ║")
    print("║  BUTTONS                                                     ║")
    print(f"║    button_strip_width:      {read_theme_value('button_strip_width'):3}  (buttons wider/narrower)  ║")
    print(f"║    content_row_spacing:     {read_theme_value('content_row_spacing'):3}  (buttons closer/apart)    ║")
    
    print("╚══════════════════════════════════════════════════════════════╝")


def show_help():
    """Display help with available commands"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              LAYOUT TUNING COMMANDS                          ║
╠══════════════════════════════════════════════════════════════╣
║  HEADER POSITION                                             ║
║    gen right [n]      Move GEN label right                   ║
║    gen left [n]       Move GEN label left                    ║
║    empty left [n]     Move selector box left                 ║
║    empty right [n]    Move selector box right                ║
║    text right [n]     Move text inside selector right        ║
║    text left [n]      Move text inside selector left         ║
║                                                              ║
║  SIZES                                                       ║
║    selector wider     Make selector box wider                ║
║    selector narrower  Make selector box narrower             ║
║    buttons wider      Make button strip wider                ║
║    buttons narrower   Make button strip narrower             ║
║                                                              ║
║  VERTICAL SPACING                                            ║
║    sliders up [n]     Move sliders up (closer to header)     ║
║    sliders down [n]   Move sliders down (more gap)           ║
║    rows closer [n]    Reduce gap between slider rows         ║
║    rows apart [n]     Increase gap between slider rows       ║
║    sliders shorter    Make sliders shorter                   ║
║    sliders taller     Make sliders taller                    ║
║                                                              ║
║  HORIZONTAL SPACING                                          ║
║    columns narrower   Make slider columns narrower           ║
║    columns wider      Make slider columns wider              ║
║    columns closer     Reduce gap between columns             ║
║    columns apart      Increase gap between columns           ║
║    buttons closer     Move buttons closer to sliders         ║
║    buttons apart      Move buttons away from sliders         ║
║                                                              ║
║  OTHER                                                       ║
║    show               Show current values                    ║
║    reset              Reset all to defaults                  ║
║    help               Show this help                         ║
╚══════════════════════════════════════════════════════════════╝

  [n] = optional amount (default: 1 for spacing, 2 for sizes)
  
  Example: python tools/tune_layout.py gen right 4
""")


def reset_to_defaults():
    """Reset all values to defaults"""
    print("\nResetting to defaults...")
    for key, value in DEFAULTS.items():
        old_value = read_theme_value(key)
        if old_value is not None:
            write_theme_value(key, value)
            print(f"  {key}: {old_value} → {value}")
    print("\n✓ All values reset to defaults")


def apply_command(element, direction, amount=None):
    """Apply a layout adjustment command"""
    cmd_key = (element.lower(), direction.lower())
    
    if cmd_key not in COMMANDS:
        print(f"✗ Unknown command: {element} {direction}")
        print("  Run 'python tools/tune_layout.py help' for available commands")
        return False
    
    theme_key, default_delta = COMMANDS[cmd_key]
    
    # Use provided amount or default
    if amount is not None:
        delta = amount if default_delta > 0 else -amount
    else:
        delta = default_delta
    
    current = read_theme_value(theme_key)
    if current is None:
        print(f"✗ Could not find {theme_key} in theme.py")
        return False
    
    new_value = write_theme_value(theme_key, current + delta)
    
    direction_word = "→" if delta > 0 else "←" if delta < 0 else "="
    print(f"✓ {theme_key}: {current} {direction_word} {new_value}")
    return True


def main():
    args = sys.argv[1:]
    
    if not args or args[0] == 'show':
        show_current_values()
        return
    
    if args[0] == 'help' or args[0] == '--help' or args[0] == '-h':
        show_help()
        return
    
    if args[0] == 'reset':
        reset_to_defaults()
        return
    
    if len(args) < 2:
        print("✗ Need at least 2 arguments: element direction [amount]")
        print("  Example: python tools/tune_layout.py gen right 4")
        print("  Run 'python tools/tune_layout.py help' for all commands")
        return
    
    element = args[0]
    direction = args[1]
    amount = int(args[2]) if len(args) > 2 else None
    
    apply_command(element, direction, amount)


if __name__ == '__main__':
    main()
